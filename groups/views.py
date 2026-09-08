from decimal import Decimal, InvalidOperation
from datetime import datetime
from xml.sax.saxutils import escape
import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .models import Group, RegistrationSession
from members.models import Member
from accounts.models import SystemLog
from accounts.views import get_client_ip


# ============================================================
# SESSION HELPERS
# ============================================================

def get_current_session():
    """
    Return the currently active registration session.

    A current session must:
        - be marked as current
        - not be completed

    The most recently created matching session is returned.
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


def get_group_for_current_session(group_id):
    """
    Return a group only when it belongs to the current
    registration session.

    This prevents old/completed-session groups from being
    accessed through manually manipulated URLs.
    """

    current_session = get_current_session()

    if not current_session:
        return None, None

    group = (
        Group.objects
        .select_related(
            'session',
            'created_by'
        )
        .filter(
            id=group_id,
            session=current_session
        )
        .first()
    )

    return group, current_session


def is_admin_user(user):
    """
    Confirm that the authenticated user is an administrator.
    """

    return (
        user.is_authenticated
        and user.is_active
        and user.is_admin
    )


def is_valid_group_leader(user):
    """
    Confirm that the authenticated user is an active group
    leader with an assigned group.
    """

    return (
        user.is_authenticated
        and user.is_active
        and user.is_group_leader
        and user.assigned_group_id is not None
    )


def get_leader_group(request):
    """
    Return the current-session group assigned to the logged-in
    group leader.

    A leader can never select another group through the URL.
    The group is obtained directly from the authenticated user.
    """

    if not is_valid_group_leader(request.user):
        return None

    group = (
        Group.objects
        .select_related('session')
        .filter(
            id=request.user.assigned_group_id
        )
        .first()
    )

    if not group:
        return None

    current_session = get_current_session()

    if not current_session:
        return None

    if group.session_id != current_session.id:
        return None

    return group


# ============================================================
# PUBLIC GROUP LIST
# ============================================================

def public_group_list(request):
    """
    Public page showing basic statistics for groups in the
    current registration session.

    Student-level information is never exposed here.

    Public information includes only:
        - Group name
        - Total members
        - Paid count
        - Unpaid count
        - Payment rate
    """

    current_session = get_current_session()

    if not current_session:
        return render(
            request,
            'groups/public_group_list.html',
            {
                'groups': [],
                'total_groups': 0,
                'current_session': None,
            }
        )

    groups = (
        Group.objects
        .filter(
            session=current_session
        )
        .order_by('name')
    )

    group_data = []

    for group in groups:
        member_count = group.get_member_count()
        paid_count = group.get_paid_count()
        unpaid_count = group.get_unpaid_count()

        payment_rate = (
            round(
                (paid_count / member_count) * 100,
                1
            )
            if member_count > 0
            else 0
        )

        group_data.append({
            'group': group,
            'member_count': member_count,
            'paid_count': paid_count,
            'unpaid_count': unpaid_count,
            'payment_rate': payment_rate,
        })

    context = {
        'groups': group_data,
        'total_groups': groups.count(),
        'current_session': current_session,
    }

    return render(
        request,
        'groups/public_group_list.html',
        context
    )


# ============================================================
# GROUP DETAIL
# ============================================================

def group_detail(request, group_id):
    """
    Display information about one group.

    Public visitors:
        - See statistics only.

    Ordinary registered students:
        - Must not receive private group information through
          this public URL.

    The assigned group leader:
        - May see the full member list of their own group.

    The important security rule is that detailed information
    is never granted merely because a group ID was supplied.
    """

    group, current_session = get_group_for_current_session(
        group_id
    )

    if not group:
        messages.error(
            request,
            "The requested group is not available in the current "
            "registration session."
        )

        return redirect(
            'groups:public_group_list'
        )

    is_leader = (
        is_valid_group_leader(request.user)
        and request.user.assigned_group_id == group.id
    )

    member_count = group.get_member_count()
    paid_count = group.get_paid_count()
    unpaid_count = group.get_unpaid_count()

    payment_rate = (
        round(
            (paid_count / member_count) * 100,
            1
        )
        if member_count > 0
        else 0
    )

    context = {
        'group': group,
        'current_session': current_session,
        'member_count': member_count,
        'paid_count': paid_count,
        'unpaid_count': unpaid_count,
        'payment_rate': payment_rate,
        'is_leader': is_leader,
        'can_manage': is_leader,
    }

    # Only the authenticated leader of this exact group
    # receives its private member list.
    if is_leader:
        context['members'] = (
            group.get_members_list()
            .order_by('full_name')
        )

    return render(
        request,
        'groups/group_detail.html',
        context
    )


# ============================================================
# LEADER DASHBOARD
# ============================================================

@login_required
def leader_dashboard(request):
    """
    Dashboard for a group leader.

    A group leader can ONLY manage the group assigned to their
    account and only while that group belongs to the current
    registration session.
    """

    group = get_leader_group(request)

    if not group:
        messages.error(
            request,
            "Access denied. You do not have a valid active "
            "group assignment."
        )

        return redirect(
            'accounts:home'
        )

    members = (
        group.get_members_list()
        .order_by('full_name')
    )

    search_query = request.GET.get(
        'search',
        ''
    ).strip()

    if search_query:
        members = members.filter(
            Q(full_name__icontains=search_query)
            | Q(matric_number__icontains=search_query)
        )

    total_members = group.get_member_count()
    paid_count = group.get_paid_count()
    unpaid_count = group.get_unpaid_count()

    payment_rate = (
        round(
            (paid_count / total_members) * 100,
            1
        )
        if total_members > 0
        else 0
    )

    context = {
        'group': group,
        'current_session': group.session,
        'members': members,
        'member_count': total_members,
        'total_members': total_members,
        'paid_count': paid_count,
        'unpaid_count': unpaid_count,
        'payment_rate': payment_rate,
        'search_query': search_query,
    }

    return render(
        request,
        'groups/leader_dashboard.html',
        context
    )


# ============================================================
# CONFIRM PAYMENT
# ============================================================

@login_required
@csrf_protect
@require_http_methods(["POST"])
def leader_confirm_payment(request, member_id):
    """
    Confirm payment for a member belonging to the logged-in
    leader's own current-session group only.
    """

    group = get_leader_group(request)

    if not group:
        messages.error(
            request,
            "Access denied. You do not have a valid active "
            "group assignment."
        )

        return redirect(
            'accounts:home'
        )

    member = get_object_or_404(
        Member,
        id=member_id,
        group=group,
        session=group.session
    )

    amount = request.POST.get(
        'amount',
        ''
    ).strip()

    if not amount:
        messages.error(
            request,
            "Please enter the amount paid."
        )

        return redirect(
            'groups:leader_dashboard'
        )

    try:
        amount_decimal = Decimal(amount)

    except (InvalidOperation, ValueError):
        messages.error(
            request,
            "Invalid amount format."
        )

        return redirect(
            'groups:leader_dashboard'
        )

    if amount_decimal <= 0:
        messages.error(
            request,
            "Amount must be greater than zero."
        )

        return redirect(
            'groups:leader_dashboard'
        )

    member.confirm_payment(
        amount_decimal,
        request.user
    )

    SystemLog.objects.create(
        user=request.user,
        action_type='PAYMENT',
        description=(
            f"Leader {request.user.username} confirmed "
            f"payment of ₦{amount_decimal} for "
            f"{member.full_name} "
            f"({member.matric_number}) in "
            f"{group.name}, session "
            f"{group.session.name}."
        ),
        ip_address=get_client_ip(request)
    )

    messages.success(
        request,
        f"Payment confirmed for {member.full_name} "
        f"(₦{amount_decimal})."
    )

    return redirect(
        'groups:leader_dashboard'
    )
# ============================================================
# REVERSE PAYMENT
# ============================================================

@login_required
@csrf_protect
@require_http_methods(["POST"])
def leader_reverse_payment(request, member_id):
    """
    Reverse payment for a member belonging to the logged-in
    leader's own current-session group only.
    """

    group = get_leader_group(request)

    if not group:
        messages.error(
            request,
            "Access denied. You do not have a valid active "
            "group assignment."
        )

        return redirect(
            'accounts:home'
        )

    member = get_object_or_404(
        Member,
        id=member_id,
        group=group,
        session=group.session
    )

    if not member.has_paid:
        messages.warning(
            request,
            f"{member.full_name} has no payment to reverse."
        )

        return redirect(
            'groups:leader_dashboard'
        )

    member.reverse_payment()

    SystemLog.objects.create(
        user=request.user,
        action_type='UPDATE',
        description=(
            f"Leader {request.user.username} reversed payment "
            f"for {member.full_name} "
            f"({member.matric_number}) in "
            f"{group.name}, session "
            f"{group.session.name}."
        ),
        ip_address=get_client_ip(request)
    )

    messages.info(
        request,
        f"Payment reversed for {member.full_name}."
    )

    return redirect(
        'groups:leader_dashboard'
    )


# ============================================================
# REMOVE MEMBER
# ============================================================

@login_required
@csrf_protect
@require_http_methods(["POST"])
def leader_delete_member(request, member_id):
    """
    Permanently remove a member from the leader's own group.

    There is deliberately no soft-delete logic.

    The member must:
        - belong to the logged-in leader's group
        - belong to that group's session

    A leader cannot remove a member from another group by
    manipulating the member ID.
    """

    group = get_leader_group(request)

    if not group:
        messages.error(
            request,
            "Access denied. You do not have a valid active "
            "group assignment."
        )

        return redirect(
            'accounts:home'
        )

    member = get_object_or_404(
        Member,
        id=member_id,
        group=group,
        session=group.session
    )

    member_name = member.full_name
    matric_number = member.matric_number

    member.delete()

    SystemLog.objects.create(
        user=request.user,
        action_type='DELETE',
        description=(
            f"Leader {request.user.username} permanently removed "
            f"member {member_name} ({matric_number}) from "
            f"{group.name}, session {group.session.name}."
        ),
        ip_address=get_client_ip(request)
    )

    messages.success(
        request,
        f"Member '{member_name}' has been removed from "
        f"the group."
    )

    return redirect(
        'groups:leader_dashboard'
    )


# ============================================================
# EXPORT ACCESS CONTROL
# ============================================================

def can_export_group(request, group):
    """
    Determine whether the authenticated user may export the
    private member information of a group.

    Group leader:
        - May export only their own assigned group.

    Administrator:
        - May export groups belonging to the current session.
        - Administrator access is not restricted to the group
          they originally created.

    Everyone else:
        - No private export access.
    """

    if not request.user.is_authenticated:
        return False

    current_session = get_current_session()

    if not current_session:
        return False

    if group.session_id != current_session.id:
        return False

    if is_valid_group_leader(request.user):
        return (
            request.user.assigned_group_id
            == group.id
        )

    if is_admin_user(request.user):
        return True

    return False


# ============================================================
# EXPORT GROUP HELPER
# ============================================================

def get_exportable_group(request, group_id):
    """
    Safely retrieve a group for export.

    The group must belong to the current registration session.
    Authorization is checked separately through
    can_export_group().
    """

    current_session = get_current_session()

    if not current_session:
        return None, None

    group = (
        Group.objects
        .select_related(
            'session'
        )
        .filter(
            id=group_id,
            session=current_session
        )
        .first()
    )

    if not group:
        return None, current_session

    if not can_export_group(request, group):
        return None, current_session

    return group, current_session


# ============================================================
# CSV EXPORT
# ============================================================

@login_required
def export_group_members_csv(request, group_id):
    """
    Export group member information as CSV.

    Access is restricted to:
        - the group's assigned leader, or
        - an administrator.

    The export contains student names, matric numbers and
    payment information because it is private operational data.
    """

    group, current_session = get_exportable_group(
        request,
        group_id
    )

    if not group:
        messages.error(
            request,
            "Access denied. You cannot export this group's data."
        )

        return redirect(
            'accounts:home'
        )

    members = (
        group.get_members_list()
        .order_by('full_name')
    )

    response = HttpResponse(
        content_type='text/csv'
    )

    response['Content-Disposition'] = (
        f'attachment; filename="{group.name}_members_'
        f'{datetime.now().strftime("%Y%m%d")}.csv"'
    )

    writer = csv.writer(response)

    writer.writerow([
        f'Course: {current_session.course_code}'
    ])

    writer.writerow([
        f'Centre: {current_session.centre_name}'
    ])

    writer.writerow([
        f'Session: {current_session.name}'
    ])

    writer.writerow([
        f'Group: {group.name}'
    ])

    writer.writerow([
        f'Exported on: '
        f'{datetime.now().strftime("%d/%m/%Y %H:%M")}'
    ])

    writer.writerow([])

    writer.writerow([
        'S/N',
        'Matric Number',
        'Full Name',
        'Payment Status',
        'Amount Paid'
    ])

    for index, member in enumerate(members, 1):
        writer.writerow([
            index,
            member.matric_number,
            member.full_name,
            (
                'Paid'
                if member.has_paid
                else 'Unpaid'
            ),
            (
                str(member.amount_paid)
                if member.amount_paid is not None
                else 'N/A'
            )
        ])

    SystemLog.objects.create(
        user=request.user,
        action_type='EXPORT',
        description=(
            f"Exported {group.name} members to CSV "
            f"for session {current_session.name}."
        ),
        ip_address=get_client_ip(request)
    )

    return response


# ============================================================
# EXCEL EXPORT
# ============================================================

@login_required
def export_group_members_excel(request, group_id):
    """
    Export full group member information as an XLSX file.

    Access is restricted to the group's assigned leader or
    an administrator.
    """

    group, current_session = get_exportable_group(
        request,
        group_id
    )

    if not group:
        messages.error(
            request,
            "Access denied. You cannot export this group's data."
        )

        return redirect(
            'accounts:home'
        )

    members = (
        group.get_members_list()
        .order_by('full_name')
    )

    workbook = Workbook()

    worksheet = workbook.active

    worksheet.title = group.name[:31]

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    worksheet.merge_cells('A1:E1')

    title_cell = worksheet['A1']

    title_cell.value = (
        f'{current_session.course_code} - '
        f'{group.name}'
    )

    title_cell.font = Font(
        size=16,
        bold=True
    )

    title_cell.alignment = Alignment(
        horizontal='center'
    )

    worksheet.merge_cells('A2:E2')

    centre_cell = worksheet['A2']

    centre_cell.value = (
        f'Centre: {current_session.centre_name}'
    )

    centre_cell.alignment = Alignment(
        horizontal='center'
    )

    worksheet.merge_cells('A3:E3')

    session_cell = worksheet['A3']

    session_cell.value = (
        f'Session: {current_session.name}'
    )

    session_cell.alignment = Alignment(
        horizontal='center'
    )

    worksheet.merge_cells('A4:E4')

    date_cell = worksheet['A4']

    date_cell.value = (
        f'Exported on: '
        f'{datetime.now().strftime("%d/%m/%Y %H:%M")}'
    )

    date_cell.font = Font(
        size=10,
        italic=True
    )

    date_cell.alignment = Alignment(
        horizontal='center'
    )

    # --------------------------------------------------------
    # TABLE HEADERS
    # --------------------------------------------------------

    headers = [
        'S/N',
        'Matric Number',
        'Full Name',
        'Payment Status',
        'Amount Paid'
    ]

    for column, header in enumerate(
        headers,
        1
    ):
        cell = worksheet.cell(
            row=6,
            column=column,
            value=header
        )

        cell.font = Font(
            bold=True,
            color='FFFFFF'
        )

        cell.fill = PatternFill(
            start_color='1a237e',
            end_color='1a237e',
            fill_type='solid'
        )

        cell.alignment = Alignment(
            horizontal='center',
            vertical='center'
        )

    # --------------------------------------------------------
    # MEMBER DATA
    # --------------------------------------------------------

    for index, member in enumerate(
        members,
        1
    ):
        row = index + 6

        worksheet.cell(
            row=row,
            column=1,
            value=index
        )

        worksheet.cell(
            row=row,
            column=2,
            value=member.matric_number
        )

        worksheet.cell(
            row=row,
            column=3,
            value=member.full_name
        )

        worksheet.cell(
            row=row,
            column=4,
            value=(
                'Paid'
                if member.has_paid
                else 'Unpaid'
            )
        )

        worksheet.cell(
            row=row,
            column=5,
            value=(
                float(member.amount_paid)
                if member.amount_paid is not None
                else None
            )
        )

    # --------------------------------------------------------
    # COLUMN WIDTHS
    # --------------------------------------------------------

    worksheet.column_dimensions['A'].width = 8
    worksheet.column_dimensions['B'].width = 20
    worksheet.column_dimensions['C'].width = 35
    worksheet.column_dimensions['D'].width = 15
    worksheet.column_dimensions['E'].width = 15

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    response = HttpResponse(
        content_type=(
            'application/vnd.openxmlformats-officedocument.'
            'spreadsheetml.sheet'
        )
    )

    response['Content-Disposition'] = (
        f'attachment; filename="{group.name}_members_'
        f'{datetime.now().strftime("%Y%m%d")}.xlsx"'
    )

    workbook.save(response)

    SystemLog.objects.create(
        user=request.user,
        action_type='EXPORT',
        description=(
            f"Exported {group.name} members to Excel "
            f"for session {current_session.name}."
        ),
        ip_address=get_client_ip(request)
    )

    return response
# ============================================================
# PDF EXPORT
# ============================================================

@login_required
def export_group_members_pdf(request, group_id):
    """
    Export full group member information as a PDF.

    Access is restricted to:
        - the group's assigned leader, or
        - an administrator.

    The PDF contains:
        - Course
        - Centre
        - Session
        - Group
        - Matric number
        - Full name
        - Payment status
        - Amount paid
    """

    group, current_session = get_exportable_group(
        request,
        group_id
    )

    if not group:
        messages.error(
            request,
            "Access denied. You cannot export this group's data."
        )

        return redirect(
            'accounts:home'
        )

    members = (
        group.get_members_list()
        .order_by('full_name')
    )

    response = HttpResponse(
        content_type='application/pdf'
    )

    response['Content-Disposition'] = (
        f'attachment; filename="{group.name}_members_'
        f'{datetime.now().strftime("%Y%m%d")}.pdf"'
    )

    document = SimpleDocTemplate(
        response,
        pagesize=landscape(letter),
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    elements = []

    styles = getSampleStyleSheet()

    # --------------------------------------------------------
    # PDF STYLES
    # --------------------------------------------------------

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=1,
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=1,
        spaceAfter=4
    )

    # --------------------------------------------------------
    # PDF HEADER
    # --------------------------------------------------------

    elements.append(
        Paragraph(
            escape(
                f'{current_session.course_code} - '
                f'{group.name}'
            ),
            title_style
        )
    )

    elements.append(
        Paragraph(
            escape(
                f'Centre: '
                f'{current_session.centre_name}'
            ),
            subtitle_style
        )
    )

    elements.append(
        Paragraph(
            escape(
                f'Session: '
                f'{current_session.name}'
            ),
            subtitle_style
        )
    )

    elements.append(
        Paragraph(
            escape(
                f'Exported on: '
                f'{datetime.now().strftime("%d/%m/%Y %H:%M")}'
            ),
            subtitle_style
        )
    )

    elements.append(
        Spacer(1, 10)
    )

    # --------------------------------------------------------
    # PDF TABLE
    # --------------------------------------------------------

    data = [[
        'S/N',
        'Matric Number',
        'Full Name',
        'Payment Status',
        'Amount Paid'
    ]]

    for index, member in enumerate(
        members,
        1
    ):
        data.append([
            str(index),
            escape(member.matric_number),
            escape(member.full_name),
            (
                'Paid'
                if member.has_paid
                else 'Unpaid'
            ),
            (
                f'₦{member.amount_paid}'
                if member.amount_paid is not None
                else 'N/A'
            )
        ])

    table = Table(
        data,
        colWidths=[
            0.6 * inch,
            1.8 * inch,
            3.2 * inch,
            1.4 * inch,
            1.4 * inch
        ],
        repeatRows=1
    )

    table_style = TableStyle([
        (
            'BACKGROUND',
            (0, 0),
            (-1, 0),
            colors.HexColor('#1a237e')
        ),
        (
            'TEXTCOLOR',
            (0, 0),
            (-1, 0),
            colors.whitesmoke
        ),
        (
            'ALIGN',
            (0, 0),
            (-1, -1),
            'CENTER'
        ),
        (
            'ALIGN',
            (2, 0),
            (2, -1),
            'LEFT'
        ),
        (
            'FONTNAME',
            (0, 0),
            (-1, 0),
            'Helvetica-Bold'
        ),
        (
            'FONTSIZE',
            (0, 0),
            (-1, 0),
            10
        ),
        (
            'FONTSIZE',
            (0, 1),
            (-1, -1),
            9
        ),
        (
            'BOTTOMPADDING',
            (0, 0),
            (-1, 0),
            8
        ),
        (
            'TOPPADDING',
            (0, 0),
            (-1, 0),
            8
        ),
        (
            'GRID',
            (0, 0),
            (-1, -1),
            0.5,
            colors.grey
        ),
        (
            'VALIGN',
            (0, 0),
            (-1, -1),
            'MIDDLE'
        ),
        (
            'ROWBACKGROUNDS',
            (0, 1),
            (-1, -1),
            [
                colors.white,
                colors.HexColor('#f5f5f5')
            ]
        ),
    ])

    table.setStyle(table_style)

    elements.append(table)

    # --------------------------------------------------------
    # BUILD PDF
    # --------------------------------------------------------

    document.build(elements)

    # --------------------------------------------------------
    # AUDIT LOG
    # --------------------------------------------------------

    SystemLog.objects.create(
        user=request.user,
        action_type='EXPORT',
        description=(
            f"Exported {group.name} members to PDF "
            f"for session {current_session.name}."
        ),
        ip_address=get_client_ip(request)
    )

    return response


# ============================================================
# GROUP MEMBER LIST FOR REGISTERED STUDENT
# ============================================================

def get_registered_member_by_matric(
    request,
    matric_number
):
    """
    Find a registered student by matric number in the
    current registration session.

    This helper is intentionally limited to the current
    session so an old registration cannot be exposed.
    """

    current_session = get_current_session()

    if not current_session:
        return None, None

    if not matric_number:
        return None, current_session

    matric_clean = (
        matric_number
        .strip()
        .upper()
    )

    member = (
        Member.objects
        .select_related(
            'group',
            'session'
        )
        .filter(
            matric_number=matric_clean,
            session=current_session
        )
        .first()
    )

    return member, current_session


def get_group_member_list_for_registered_student(
    member
):
    """
    Return the full member list for the registered student's
    own group.

    This is intentionally based on the Member object rather
    than a group ID supplied by the browser.

    Therefore, a student cannot simply change a URL parameter
    to request another group's member list.
    """

    if not member:
        return Member.objects.none()

    return (
        Member.objects
        .filter(
            group=member.group,
            session=member.session
        )
        .order_by('full_name')
    )


# ============================================================
# REGISTERED STUDENT GROUP LIST
# ============================================================

def registered_group_members(request):
    """
    Allow a registered student to retrieve the member list
    of their own group.

    Authentication is based on the student's matric number
    for the current registration session.

    Information returned:
        - Student's own registration details
        - Full names of group members
        - Full matric numbers of group members

    Payment information for other members is NOT exposed.
    """

    current_session = get_current_session()

    if not current_session:
        messages.error(
            request,
            "There is currently no active registration session."
        )

        return render(
            request,
            'members/registered_view.html',
            {
                'current_session': None
            }
        )

    matric_number = request.GET.get(
        'matric_number',
        ''
    ).strip().upper()

    if not matric_number:
        messages.error(
            request,
            "Please provide your matric number."
        )

        return redirect(
            'members:registered_view'
        )

    member, current_session = (
        get_registered_member_by_matric(
            request,
            matric_number
        )
    )

    if not member:
        messages.error(
            request,
            f"No registration was found for matric number "
            f"'{matric_number}' in the current session."
        )

        return redirect(
            'members:registered_view'
        )

    group_members = (
        get_group_member_list_for_registered_student(
            member
        )
    )

    context = {
        'member': member,
        'group': member.group,
        'current_session': current_session,
        'group_members': group_members,
        'member_count': group_members.count(),
    }

    return render(
        request,
        'members/member_details.html',
        context
    )


# ============================================================
# COPY-FRIENDLY GROUP MEMBER DATA
# ============================================================

def registered_group_members_text(
    request
):
    """
    Return a plain-text copy of the registered student's own
    group member list.

    The output contains only:
        - S/N
        - Full Name
        - Matric Number

    Payment information is deliberately excluded.

    This endpoint is useful for copying the list into a
    Word document or DES303 report.
    """

    current_session = get_current_session()

    if not current_session:
        return HttpResponse(
            "There is currently no active registration session.",
            content_type='text/plain'
        )

    matric_number = request.GET.get(
        'matric_number',
        ''
    ).strip().upper()

    member, current_session = (
        get_registered_member_by_matric(
            request,
            matric_number
        )
    )

    if not member:
        return HttpResponse(
            "Registration not found for the supplied matric number.",
            status=404,
            content_type='text/plain'
        )

    group_members = (
        get_group_member_list_for_registered_student(
            member
        )
    )

    lines = [
        f'Course: {current_session.course_code}',
        f'Centre: {current_session.centre_name}',
        f'Session: {current_session.name}',
        f'Group: {member.group.name}',
        '',
        'S/N\tFull Name\tMatric Number'
    ]

    for index, group_member in enumerate(
        group_members,
        1
    ):
        lines.append(
            f'{index}\t'
            f'{group_member.full_name}\t'
            f'{group_member.matric_number}'
        )

    response = HttpResponse(
        '\n'.join(lines),
        content_type='text/plain'
    )

    response['Content-Disposition'] = (
        f'attachment; filename="{member.group.name}_'
        f'member_list.txt"'
    )

    return response
# ============================================================
# REGISTERED STUDENT GROUP LIST - POST VERSION
# ============================================================

@csrf_protect
@require_http_methods(["GET", "POST"])
def registered_group_members_view(request):
    """
    Dedicated view for a registered student to access the
    full member list of their own group.

    The matric number identifies the student's registration
    in the current session.

    GET:
        Displays the lookup form.

    POST:
        Validates the matric number and displays the student's
        own group member list.
    """

    current_session = get_current_session()

    if not current_session:
        messages.error(
            request,
            "There is currently no active registration session."
        )

        return redirect(
            'members:registered_view'
        )

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

            return redirect(
                'members:registered_view'
            )

        member, current_session = (
            get_registered_member_by_matric(
                request,
                matric_number
            )
        )

        if not member:
            messages.error(
                request,
                f"No registration was found for matric number "
                f"'{matric_number}' in the current session."
            )

            return redirect(
                'members:registered_view'
            )

        group_members = (
            get_group_member_list_for_registered_student(
                member
            )
        )

        context = {
            'member': member,
            'group': member.group,
            'current_session': current_session,
            'group_members': group_members,
            'member_count': group_members.count(),
        }

        return render(
            request,
            'members/member_details.html',
            context
        )

    return redirect(
        'members:registered_view'
    )


# ============================================================
# ADMIN GROUP ACCESS HELPER
# ============================================================

def get_admin_group(request, group_id):
    """
    Return a group from the current session only when the
    authenticated user is an administrator.

    This helper is intended for future administrator group
    management functions.

    It deliberately does not grant administrators access to
    completed or previous sessions through a current-session
    management URL.
    """

    if not is_admin_user(request.user):
        return None

    current_session = get_current_session()

    if not current_session:
        return None

    return (
        Group.objects
        .select_related(
            'session'
        )
        .filter(
            id=group_id,
            session=current_session
        )
        .first()
    )


# ============================================================
# GROUP STATISTICS HELPER
# ============================================================

def get_group_statistics(group):
    """
    Return reusable statistics for a group.

    This keeps calculation logic consistent between the public
    group page, leader dashboard and other future views.
    """

    member_count = group.get_member_count()
    paid_count = group.get_paid_count()
    unpaid_count = group.get_unpaid_count()

    payment_rate = (
        round(
            (paid_count / member_count) * 100,
            1
        )
        if member_count > 0
        else 0
    )

    return {
        'member_count': member_count,
        'total_members': member_count,
        'paid_count': paid_count,
        'unpaid_count': unpaid_count,
        'payment_rate': payment_rate,
    }


# ============================================================
# GROUP PRIVATE MEMBER DATA
# ============================================================

def get_private_group_members(
    request,
    group
):
    """
    Return private member information only when the requester
    is authorized for the supplied group.

    Authorized users:
        - The group's assigned leader.
        - An administrator.

    This helper is intended for future private group pages.
    """

    if not request.user.is_authenticated:
        return Member.objects.none()

    current_session = get_current_session()

    if not current_session:
        return Member.objects.none()

    if group.session_id != current_session.id:
        return Member.objects.none()

    if is_valid_group_leader(request.user):
        if request.user.assigned_group_id != group.id:
            return Member.objects.none()

    elif is_admin_user(request.user):
        pass

    else:
        return Member.objects.none()

    return (
        Member.objects
        .filter(
            group=group,
            session=current_session
        )
        .order_by('full_name')
    )


# ============================================================
# GROUP MEMBER LIST DATA FOR REPORT USE
# ============================================================

def build_group_member_list(group):
    """
    Build a simple list containing only the information that
    registered students are allowed to copy into their report.

    No payment information is included.
    """

    members = (
        Member.objects
        .filter(
            group=group,
            session=group.session
        )
        .order_by('full_name')
    )

    return [
        {
            'number': index,
            'full_name': member.full_name,
            'matric_number': member.matric_number,
        }
        for index, member in enumerate(
            members,
            1
        )
    ]


# ============================================================
# GROUP MEMBER LIST TEXT RESPONSE
# ============================================================

def registered_group_members_copy(request):
    """
    Return a copy-friendly plain-text member list for a
    registered student.

    The student must prove membership by supplying a matric
    number belonging to the current session.

    Only names and matric numbers are returned.
    """

    current_session = get_current_session()

    if not current_session:
        return HttpResponse(
            "There is currently no active registration session.",
            status=404,
            content_type='text/plain'
        )

    matric_number = request.GET.get(
        'matric_number',
        ''
    ).strip().upper()

    member, current_session = (
        get_registered_member_by_matric(
            request,
            matric_number
        )
    )

    if not member:
        return HttpResponse(
            "Registration not found.",
            status=404,
            content_type='text/plain'
        )

    member_list = build_group_member_list(
        member.group
    )

    lines = [
        (
            f'{current_session.course_code} '
            f'Group Member List'
        ),
        f'Centre: {current_session.centre_name}',
        f'Session: {current_session.name}',
        f'Group: {member.group.name}',
        '',
        'S/N    Full Name    Matric Number',
        '-' * 60,
    ]

    for item in member_list:
        lines.append(
            f"{item['number']}. "
            f"{item['full_name']}    "
            f"{item['matric_number']}"
        )

    return HttpResponse(
        '\n'.join(lines),
        content_type='text/plain'
    )


# ============================================================
# SECURITY FALLBACK
# ============================================================

def group_access_denied(request):
    """
    Generic access-denied response for future group-management
    routes.

    Kept as a dedicated helper so future management views can
    use consistent access-denied behavior.
    """

    messages.error(
        request,
        "You do not have permission to access this group."
    )

    return redirect(
        'accounts:home'
    )