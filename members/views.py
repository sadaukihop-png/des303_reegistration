from django.contrib import messages
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from .models import Member
from groups.models import Group, RegistrationSession
from accounts.models import SystemLog
from accounts.views import get_client_ip


# ============================================================
# HELPER
# ============================================================

def get_current_session():
    """
    Return the current open registration session.

    A session must be current and not completed before students
    can register or view current registration records.
    """

    return (
        RegistrationSession.objects
        .filter(
            is_current=True,
            is_completed=False
        )
        .order_by('-created_at')
        .first()
    )


def get_registration_context(request, groups=None):
    """
    Build the common context used by the registration page.
    """

    current_session = get_current_session()

    if groups is None:
        if current_session:
            groups = (
                Group.objects
                .filter(session=current_session)
                .order_by('name')
            )
        else:
            groups = Group.objects.none()

    return {
        'current_session': current_session,
        'groups': groups,
    }


# ============================================================
# GUEST REGISTRATION
# ============================================================

@csrf_protect
@require_http_methods(["GET", "POST"])
def guest_register(request):
    """
    Public student registration.

    Students can register only in the current open
    registration session.
    """

    current_session = get_current_session()

    # --------------------------------------------------------
    # No active registration session
    # --------------------------------------------------------

    if not current_session:
        messages.error(
            request,
            "Student registration is currently closed. "
            "There is no active registration session."
        )

        return render(
            request,
            'members/guest_register.html',
            {
                'current_session': None,
                'groups': Group.objects.none(),
            }
        )

    groups = (
        Group.objects
        .filter(session=current_session)
        .order_by('name')
    )

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    if request.method == 'POST':

        group_id = request.POST.get(
            'group_id',
            ''
        ).strip()

        full_name = request.POST.get(
            'full_name',
            ''
        ).strip()

        matric_number = request.POST.get(
            'matric_number',
            ''
        ).strip().upper()

        # ----------------------------------------------------
        # Basic validation
        # ----------------------------------------------------

        if not group_id:
            messages.error(
                request,
                "Please select your group."
            )

            return render(
                request,
                'members/guest_register.html',
                get_registration_context(
                    request,
                    groups
                )
            )

        if not full_name:
            messages.error(
                request,
                "Please enter your full name."
            )

            return render(
                request,
                'members/guest_register.html',
                get_registration_context(
                    request,
                    groups
                )
            )

        if not matric_number:
            messages.error(
                request,
                "Please enter your matric number."
            )

            return render(
                request,
                'members/guest_register.html',
                get_registration_context(
                    request,
                    groups
                )
            )

        # ----------------------------------------------------
        # Validate selected group
        # ----------------------------------------------------

        group = (
            Group.objects
            .filter(
                id=group_id,
                session=current_session
            )
            .first()
        )

        if not group:
            messages.error(
                request,
                "The selected group is not available "
                "in the current registration session."
            )

            return render(
                request,
                'members/guest_register.html',
                get_registration_context(
                    request,
                    groups
                )
            )

        # ----------------------------------------------------
        # Duplicate check
        # ----------------------------------------------------

        exists, existing_group = (
            Member.check_duplicate_registration(
                matric_number,
                session=current_session
            )
        )

        if exists:
            messages.error(
                request,
                f"Matric number '{matric_number}' is already "
                f"registered in '{existing_group}' for this session."
            )

            return render(
                request,
                'members/guest_register.html',
                get_registration_context(
                    request,
                    groups
                )
            )

        # ----------------------------------------------------
        # Create member
        # ----------------------------------------------------

        try:
            with transaction.atomic():

                member = Member.objects.create(
                    matric_number=matric_number,
                    full_name=full_name,
                    session=current_session,
                    group=group
                )

        except IntegrityError:
            # Handles two people attempting to register the
            # same matric number at almost exactly the same time.
            messages.error(
                request,
                f"Matric number '{matric_number}' has already "
                f"been registered for this session."
            )

            return render(
                request,
                'members/guest_register.html',
                get_registration_context(
                    request,
                    groups
                )
            )

        # ----------------------------------------------------
        # Audit log
        # ----------------------------------------------------

        SystemLog.objects.create(
            user=None,
            action_type='REGISTER',
            description=(
                f"Student registered "
                f"{member.full_name} "
                f"({member.matric_number}) "
                f"in group '{group.name}' "
                f"for session '{current_session.name}'."
            ),
            ip_address=get_client_ip(request)
        )

        messages.success(
            request,
            f"Registration successful! "
            f"You are now a member of '{group.name}'."
        )

        return render(
            request,
            'members/registration_success.html',
            {
                'member': member,
                'group': group,
                'current_session': current_session,
            }
        )

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    return render(
        request,
        'members/guest_register.html',
        {
            'current_session': current_session,
            'groups': groups,
        }
    )


# ============================================================
# REGISTERED MEMBER VIEW
# ============================================================

@csrf_protect
@require_http_methods(["GET", "POST"])
def registered_view(request):
    """
    Allow a registered student to retrieve their registration
    using their matric number.

    Only the record belonging to the current registration
    session is returned.
    """

    current_session = get_current_session()

    # --------------------------------------------------------
    # No current session
    # --------------------------------------------------------

    if not current_session:
        messages.error(
            request,
            "There is currently no active registration session."
        )

        return render(
            request,
            'members/registered_view.html'
        )

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    if request.method == 'POST':

        matric_number = request.POST.get(
            'matric_number',
            ''
        ).strip().upper()

        if not matric_number:
            messages.error(
                request,
                "Please enter your matric number."
            )

            return render(
                request,
                'members/registered_view.html'
            )

        # ----------------------------------------------------
        # Find ONLY current-session registration
        # ----------------------------------------------------

        member = (
            Member.objects
            .select_related(
                'group',
                'session'
            )
            .filter(
                matric_number=matric_number,
                session=current_session
            )
            .first()
        )

        if not member:
            messages.error(
                request,
                f"No registration found for matric number "
                f"'{matric_number}' in the current session."
            )

            return render(
                request,
                'members/registered_view.html',
                {
                    'current_session': current_session
                }
            )

        # ----------------------------------------------------
        # Get this student's group members
        # ----------------------------------------------------

        group_members = (
            member.group
            .get_members_list()
        )

        member_count = group_members.count()

        paid_count = (
            member.group.get_paid_count()
        )

        unpaid_count = (
            member.group.get_unpaid_count()
        )

        payment_rate = (
            member.group.get_payment_rate()
        )

        # ----------------------------------------------------
        # Student-facing member list
        # ----------------------------------------------------
        #
        # IMPORTANT:
        # The template should display only:
        #
        #   Full Name
        #   Matric Number
        #
        # It must NOT display:
        #
        #   amount_paid
        #   payment_confirmed_by
        #   payment_confirmed_at
        #   other students' payment status
        #

        context = {
            'member': member,
            'group': member.group,
            'current_session': current_session,
            'group_members': group_members,
            'member_count': member_count,
            'paid_count': paid_count,
            'unpaid_count': unpaid_count,
            'payment_rate': payment_rate,
        }

        return render(
            request,
            'members/member_details.html',
            context
        )

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    return render(
        request,
        'members/registered_view.html',
        {
            'current_session': current_session
        }
    )