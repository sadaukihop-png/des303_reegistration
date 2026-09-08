from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal

class Member(models.Model):
"""
Student registered in a DES303 group for a specific
registration session.
"""

# Personal Information
matric_number = models.CharField(
    max_length=20,
    db_index=True,
    help_text="Student matric number"
)

full_name = models.CharField(
    max_length=200,
    help_text="Student full name"
)

# Registration session
session = models.ForeignKey(
    'groups.RegistrationSession',
    on_delete=models.CASCADE,
    related_name='members',
    help_text="Registration session for this student"
)

# Group association
group = models.ForeignKey(
    'groups.Group',
    on_delete=models.CASCADE,
    related_name='members',
    help_text="Group this member belongs to"
)

# Payment Information
has_paid = models.BooleanField(
    default=False,
    help_text="Payment status"
)

amount_paid = models.DecimalField(
    max_digits=10,
    decimal_places=2,
    null=True,
    blank=True,
    help_text="Amount paid by member"
)

payment_confirmed_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='confirmed_payments',
    help_text="Group leader who confirmed payment"
)

payment_confirmed_at = models.DateTimeField(
    null=True,
    blank=True
)

# Timestamps
registered_at = models.DateTimeField(
    auto_now_add=True
)

updated_at = models.DateTimeField(
    auto_now=True
)

class Meta:
    db_table = 'members'
    verbose_name = 'Member'
    verbose_name_plural = 'Members'
    ordering = ['full_name']

    constraints = [
        models.UniqueConstraint(
            fields=['session', 'matric_number'],
            name='unique_matric_per_session'
        )
    ]

def __str__(self):
    return (
        f"{self.full_name} "
        f"({self.matric_number}) - "
        f"{self.group.name}"
    )

def save(self, *args, **kwargs):
    """
    Normalize matric number before saving.
    """
    if self.matric_number:
        self.matric_number = (
            self.matric_number.strip().upper()
        )

    super().save(*args, **kwargs)

def confirm_payment(self, amount, confirmed_by_user):
    """
    Confirm payment for this member.
    """
    self.has_paid = True
    self.amount_paid = Decimal(str(amount))
    self.payment_confirmed_by = confirmed_by_user
    self.payment_confirmed_at = timezone.now()

    self.save(
        update_fields=[
            'has_paid',
            'amount_paid',
            'payment_confirmed_by',
            'payment_confirmed_at',
            'updated_at'
        ]
    )

def reverse_payment(self):
    """
    Reverse payment confirmation.
    """
    self.has_paid = False
    self.amount_paid = None
    self.payment_confirmed_by = None
    self.payment_confirmed_at = None

    self.save(
        update_fields=[
            'has_paid',
            'amount_paid',
            'payment_confirmed_by',
            'payment_confirmed_at',
            'updated_at'
        ]
    )

def get_payment_status_display(self):
    """
    Get human-readable payment status.
    """
    if self.has_paid:
        return f"Paid (₦{self.amount_paid})"

    return "Unpaid"

@classmethod
def find_by_matric(cls, matric_number, session=None):
    """
    Find a student by matric number.

    If a session is supplied, only that session is searched.
    """
    if not matric_number:
        return None

    matric_clean = matric_number.strip().upper()

    queryset = cls.objects.filter(
        matric_number=matric_clean
    )

    if session is not None:
        queryset = queryset.filter(
            session=session
        )

    return queryset.first()

@classmethod
def check_duplicate_registration(
    cls,
    matric_number,
    session
):
    """
    Check whether a matric number is already registered
    in the supplied session.

    Returns:
        (exists, group_name)
    """
    member = cls.find_by_matric(
        matric_number,
        session=session
    )

    if member:
        return True, member.group.name

    return False, None