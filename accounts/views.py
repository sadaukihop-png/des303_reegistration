from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django_ratelimit.decorators import ratelimit

from .forms import AdminLoginForm, GroupLeaderLoginForm
from .models import CustomUser, LoginAttempt, SystemLog
from groups.models import Group, RegistrationSession
from members.models import Member


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_client_ip(request):
    """
    Get the client's IP address.

    When deployed behind a proxy, the first address in
    X-Forwarded-For is used.
    """

    x_forwarded_for = request.META.get(
        'HTTP_X_FORWARDED_FOR'
    )

    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()

    return request.META.get('REMOTE_ADDR')


def log_system_action(
    user,
    action_type,
    description,
    request
):
    """
    Record an important system action in the audit log.
    """

    SystemLog.objects.create(
        user=user,
        action_type=action_type,
        description=description,
        ip_address=get_client_ip(request)
    )


def get_current_session():
    """
    Return the current registration session.

    Only a session that is both current and not completed
    can accept new registrations.
    """

    return RegistrationSession.objects.filter(
        is_current=True,
        is_completed=False
    ).order_by('-created_at').first()


def is_admin_user(user):
    """
    Check whether the authenticated user is an active
    system administrator.
    """

    return (
        user.is_authenticated
        and user.is_active
        and user.is_admin
    )


def is_group_leader_user(user):
    """
    Check whether the authenticated user is an active
    group leader with an assigned group.
    """

    return (
        user.is_authenticated
        and user.is_active
        and user.is_group_leader
        and user.assigned_group is not None
    )


# ============================================================
# HOME PAGE
# ============================================================

def home(request):
    """
    Public landing page.

    Only statistics from the current registration session
    are displayed.
    """

    current_session = get_current_session()

    if current_session:
        groups = current_session.groups.all()

        total_groups = groups.count()

        total_members = Member.objects.filter(
            session=current_session
        ).count()

    else:
        total_groups = 0
        total_members = 0

    context = {
        'current_session': current_session,
        'total_groups': total_groups,
        'total_members': total_members,
    }

    return render(
        request,
        'index.html',
        context
    )


# ============================================================
# ADMIN AUTHENTICATION
# ============================================================

@ratelimit(
    key='ip',
    rate='5/m',
    method='POST'
)
@csrf_protect
@require_http_methods(["GET", "POST"])
def admin_login_view(request):
    """
    University staff administrator login.
    """

    if is_admin_user(request.user):
        return redirect(
            'accounts:admin_dashboard'
        )

    if request.method == 'POST':
        form = AdminLoginForm(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(
                request,
                username=username,
                password=password
            )

            if user is not None and user.is_admin:
                login(request, user)

                LoginAttempt.objects.create(
                    username=username,
                    ip_address=get_client_ip(request),
                    successful=True
                )

                log_system_action(
                    user=user,
                    action_type='LOGIN',
                    description=(
                        f"Administrator {user.username} logged in."
                    ),
                    request=request
                )

                messages.success(
                    request,
                    f"Welcome Admin {user.username}!"
                )

                return redirect(
                    'accounts:admin_dashboard'
                )

            LoginAttempt.objects.create(
                username=username,
                ip_address=get_client_ip(request),
                successful=False
            )

            messages.error(
                request,
                "Invalid administrator credentials."
            )

    else:
        form = AdminLoginForm()

    return render(
        request,
        'accounts/admin_login.html',
        {'form': form}
    )


# ============================================================
# GROUP LEADER AUTHENTICATION
# ============================================================

@ratelimit(
    key='ip',
    rate='5/m',
    method='POST'
)
@csrf_protect
@require_http_methods(["GET", "POST"])
def group_leader_login_view(request):
    """
    Group leader login.

    Leaders can only authenticate against a group belonging
    to the current registration session.
    """

    if is_group_leader_user(request.user):
        return redirect(
            'groups:leader_dashboard'
        )

    current_session = get_current_session()

    if not current_session:
        messages.error(
            request,
            "There is currently no active registration session."
        )

        return render(
            request,
            'accounts/leader_login.html'
        )

    if request.method == 'POST':
        form = GroupLeaderLoginForm(request.POST)

        if form.is_valid():
            group_name = form.cleaned_data[
                'group_name'
            ].strip()

            password = form.cleaned_data[
                'password'
            ]

            group = Group.objects.filter(
                session=current_session,
                name__iexact=group_name
            ).first()

            if not group:
                LoginAttempt.objects.create(
                    username=group_name,
                    ip_address=get_client_ip(request),
                    successful=False
                )

                messages.error(
                    request,
                    "Group not found in the current registration session."
                )

                return render(
                    request,
                    'accounts/leader_login.html',
                    {'form': form}
                )

            leader = group.get_leader()

            if not leader:
                messages.error(
                    request,
                    "No leader is assigned to this group. "
                    "Please contact the administrator."
                )

                return render(
                    request,
                    'accounts/leader_login.html',
                    {'form': form}
                )

            if not leader.is_active:
                messages.error(
                    request,
                    "This group leader account is currently disabled."
                )

                return render(
                    request,
                    'accounts/leader_login.html',
                    {'form': form}
                )

            if group.check_leader_password(password):
                login(request, leader)

                leader.last_login_ip = get_client_ip(
                    request
                )

                leader.save(
                    update_fields=[
                        'last_login_ip',
                        'updated_at'
                    ]
                )

                LoginAttempt.objects.create(
                    username=leader.username,
                    ip_address=get_client_ip(request),
                    successful=True
                )

                log_system_action(
                    user=leader,
                    action_type='LOGIN',
                    description=(
                        f"Group Leader {leader.username} "
                        f"logged in for {group.name} "
                        f"({current_session.name})."
                    ),
                    request=request
                )

                messages.success(
                    request,
                    f"Welcome {leader.username}!"
                )

                return redirect(
                    'groups:leader_dashboard'
                )

            LoginAttempt.objects.create(
                username=group_name,
                ip_address=get_client_ip(request),
                successful=False
            )

            messages.error(
                request,
                "Invalid group leader password."
            )

    else:
        form = GroupLeaderLoginForm()

    return render(
        request,
        'accounts/leader_login.html',
        {
            'form': form,
            'current_session': current_session,
        }
    )


# ============================================================
# LOGOUT
# ============================================================

@require_http_methods(["GET", "POST"])
def logout_view(request):
    """
    Log the user out and record the action.
    """

    if request.user.is_authenticated:
        log_system_action(
            user=request.user,
            action_type='LOGOUT',
            description=(
                f"{request.user.username} logged out."
            ),
            request=request
        )

    logout(request)

    messages.info(
        request,
        "You have been logged out successfully."
    )

    return redirect(
        'accounts:home'
    )


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@login_required
def admin_dashboard(request):
    """
    Main dashboard for the university administrator.

    The administrator can see all groups in the current
    registration session, regardless of which group was created
    first, because the administrator coordinates the entire
    activity.
    """

    if not is_admin_user(request.user):
        messages.error(
            request,
            "Access denied. Administrator privileges required."
        )

        return redirect(
            'accounts:home'
        )

    current_session = get_current_session()

    if current_session:
        groups = (
            Group.objects
            .filter(session=current_session)
            .select_related('session')
            .prefetch_related('leaders')
            .order_by('name')
        )

        total_groups = groups.count()

        total_members = Member.objects.filter(
            session=current_session
        ).count()

        total_paid = Member.objects.filter(
            session=current_session,
            has_paid=True
        ).count()

        total_unpaid = total_members - total_paid

        if total_members:
            payment_rate = round(
                (total_paid / total_members) * 100,
                2
            )
        else:
            payment_rate = 0

    else:
        groups = Group.objects.none()
        total_groups = 0
        total_members = 0
        total_paid = 0
        total_unpaid = 0
        payment_rate = 0

    context = {
        'current_session': current_session,
        'groups': groups,
        'total_groups': total_groups,
        'total_members': total_members,
        'total_paid': total_paid,
        'total_unpaid': total_unpaid,
        'payment_rate': payment_rate,
    }

    return render(
        request,
        'accounts/admin_dashboard.html',
        context
    )


# ============================================================
# CREATE GROUP
# ============================================================

@login_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def admin_create_group(request):
    """
    Administrator creates a group inside the current
    registration session.

    A secure leader password is generated and displayed once
    to the administrator.
    """

    if not is_admin_user(request.user):
        messages.error(
            request,
            "Access denied."
        )

        return redirect(
            'accounts:home'
        )

    current_session = get_current_session()

    if not current_session:
        messages.error(
            request,
            "No current registration session exists. "
            "Create or activate a registration session first."
        )

        return redirect(
            'accounts:admin_dashboard'
        )

    if request.method == 'POST':
        group_name = request.POST.get(
            'group_name',
            ''
        ).strip()

        description = request.POST.get(
            'description',
            ''
        ).strip()

        if not group_name:
            messages.error(
                request,
                "Group name is required."
            )

            return redirect(
                'accounts:admin_create_group'
            )

        if Group.objects.filter(
            session=current_session,
            name__iexact=group_name
        ).exists():
            messages.error(
                request,
                f"Group '{group_name}' already exists "
                f"in the current session."
            )

            return redirect(
                'accounts:admin_create_group'
            )

        try:
            with transaction.atomic():

                # Create the group first.
                group = Group.objects.create(
                    name=group_name,
                    description=description,
                    session=current_session,
                    created_by=request.user
                )

                # Generate a secure leader password.
                leader_password = (
                    group.set_leader_password()
                )

                # Generate a unique username.
                base_username = (
                    'leader_'
                    + group_name.lower()
                    .replace(' ', '_')
                )

                leader_username = base_username
                counter = 1

                while CustomUser.objects.filter(
                    username=leader_username
                ).exists():
                    leader_username = (
                        f"{base_username}_{counter}"
                    )
                    counter += 1

                # Create the leader account.
                CustomUser.objects.create_user(
                    username=leader_username,
                    password=leader_password,
                    is_group_leader=True,
                    assigned_group=group,
                    first_name=f"Leader of {group_name}"
                )

        except IntegrityError:
            messages.error(
                request,
                "The group could not be created because "
                "another group with the same name already exists "
                "in this session."
            )

            return redirect(
                'accounts:admin_create_group'
            )

        log_system_action(
            user=request.user,
            action_type='CREATE',
            description=(
                f"Administrator created group "
                f"'{group_name}' in session "
                f"'{current_session.name}' "
                f"with leader {leader_username}."
            ),
            request=request
        )

        context = {
            'group': group,
            'current_session': current_session,
            'leader_username': leader_username,
            'leader_password': leader_password,
            'created': True
        }

        messages.success(
            request,
            f"Group '{group_name}' created successfully."
        )

        return render(
            request,
            'accounts/admin_create_group.html',
            context
        )

    return render(
        request,
        'accounts/admin_create_group.html',
        {
            'current_session': current_session
        }
    )


# ============================================================
# REGENERATE GROUP LEADER PASSWORD
# ============================================================

@login_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def admin_regenerate_leader_password(
    request,
    group_id
):
    """
    Administrator regenerates the password for a specific
    group's leader.

    The previous password becomes invalid immediately.

    The new plaintext password is displayed only once.
    """

    if not is_admin_user(request.user):
        messages.error(
            request,
            "Access denied."
        )

        return redirect(
            'accounts:home'
        )

    current_session = get_current_session()

    if not current_session:
        messages.error(
            request,
            "There is no current registration session."
        )

        return redirect(
            'accounts:admin_dashboard'
        )

    group = get_object_or_404(
        Group,
        id=group_id,
        session=current_session
    )

    leader = group.get_leader()

    if not leader:
        messages.error(
            request,
            "This group does not have an assigned leader."
        )

        return redirect(
            'accounts:admin_dashboard'
        )

    if request.method == 'POST':
        new_password = (
            group.regenerate_leader_password()
        )

        log_system_action(
            user=request.user,
            action_type='PASSWORD',
            description=(
                f"Administrator regenerated the leader "
                f"password for group '{group.name}' "
                f"in session '{current_session.name}'."
            ),
            request=request
        )

        return render(
            request,
            'accounts/admin_create_group.html',
            {
                'group': group,
                'current_session': current_session,
                'leader_username': leader.username,
                'leader_password': new_password,
                'password_regenerated': True,
            }
        )

    return render(
        request,
        'accounts/admin_create_group.html',
        {
            'group': group,
            'current_session': current_session,
            'leader_username': leader.username,
            'regenerate_confirmation': True,
        }
)
