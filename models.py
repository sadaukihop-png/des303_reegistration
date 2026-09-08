from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class CustomUser(AbstractUser):
    """
    Custom user model for the DES303 platform.

    Supported roles:
        1. Administrator
        2. Group Leader

    Registered students do not receive user accounts.
    Their registration is stored in the Member model.
    """

    # ---------------------------------------------------------
    # ROLE FLAGS
    # ---------------------------------------------------------

    is_admin = models.BooleanField(
        default=False,
        help_text="Designates this user as a system administrator."
    )

    is_group_leader = models.BooleanField(
        default=False,
        help_text="Designates this user as a group leader."
    )

    # ---------------------------------------------------------
    # GROUP ASSIGNMENT
    # ---------------------------------------------------------

    assigned_group = models.ForeignKey(
        'groups.Group',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leaders',
        help_text="Group managed by this group leader."
    )

    # ---------------------------------------------------------
    # ACCOUNT INFORMATION
    # ---------------------------------------------------------

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    last_login_ip = models.GenericIPAddressField(
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'custom_users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

        constraints = [
            models.UniqueConstraint(
                fields=['assigned_group'],
                condition=Q(
                    is_group_leader=True,
                    assigned_group__isnull=False
                ),
                name='unique_leader_per_group'
            )
        ]

    def __str__(self):
        if self.is_admin:
            return f"Admin: {self.username}"

        if self.is_group_leader:
            group_name = (
                self.assigned_group.name
                if self.assigned_group
                else 'Unassigned'
            )

            return (
                f"Group Leader: "
                f"{self.username} ({group_name})"
            )

        return self.username

    # ---------------------------------------------------------
    # VALIDATION
    # ---------------------------------------------------------

    def clean(self):
        """
        Validate the relationship between role and group.
        """

        super().clean()

        if self.is_group_leader and not self.assigned_group:
            raise ValidationError(
                "A group leader must be assigned to a group."
            )

        if self.is_admin and self.is_group_leader:
            raise ValidationError(
                "A user cannot be both an administrator "
                "and a group leader."
            )

    # ---------------------------------------------------------
    # ROLE HELPERS
    # ---------------------------------------------------------

    def is_super_admin(self):
        """
        Return True if this user is a system administrator.
        """
        return self.is_admin

    def get_role_display(self):
        """
        Return a human-readable role name.
        """

        if self.is_admin:
            return "Administrator"

        if self.is_group_leader:
            return "Group Leader"

        return "User"

    def get_managed_group(self):
        """
        Return the group managed by this leader.

        Returns None for administrators or unassigned users.
        """

        if not self.is_group_leader:
            return None

        return self.assigned_group


class LoginAttempt(models.Model):
    """
    Records successful and failed login attempts.

    No password is ever stored here.
    """

    username = models.CharField(
        max_length=150
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )

    timestamp = models.DateTimeField(
        auto_now_add=True
    )

    successful = models.BooleanField(
        default=False
    )

    class Meta:
        db_table = 'login_attempts'
        verbose_name = 'Login Attempt'
        verbose_name_plural = 'Login Attempts'
        ordering = ['-timestamp']

    def __str__(self):
        status = (
            "Success"
            if self.successful
            else "Failed"
        )

        return (
            f"{self.username} - "
            f"{self.timestamp} - "
            f"{status}"
        )


class SystemLog(models.Model):
    """
    Security and operational audit log.

    Important actions such as registration, payment confirmation,
    password regeneration, login, deletion and export can be
    recorded here.
    """

    ACTION_TYPES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('PAYMENT', 'Payment Confirmation'),
        ('EXPORT', 'Export Data'),
        ('REGISTER', 'Student Registration'),
        ('PASSWORD', 'Password Regeneration'),
    ]

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='system_logs'
    )

    action_type = models.CharField(
        max_length=20,
        choices=ACTION_TYPES
    )

    description = models.TextField()

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )

    timestamp = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        db_table = 'system_logs'
        verbose_name = 'System Log'
        verbose_name_plural = 'System Logs'
        ordering = ['-timestamp']

    def __str__(self):
        return (
            f"{self.get_action_type_display()} - "
            f"{self.timestamp}"
        )