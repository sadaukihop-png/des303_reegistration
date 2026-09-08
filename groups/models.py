from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
import secrets
import string


class RegistrationSession(models.Model):
    """
    Represents one temporary DES303 registration cycle.

    Example:
        DES303 - 2026_2
        DES303 - 2027_1

    A session contains its groups and registered students.
    When the session is completed, the administrator can export
    the required records and later permanently clear the session.
    """

    name = models.CharField(
        max_length=50,
        unique=True,
        help_text="Session name, e.g. 2026_2"
    )

    course_code = models.CharField(
        max_length=20,
        default="DES303"
    )

    centre_name = models.CharField(
        max_length=200,
        default="Abuja Model Study Centre"
    )

    is_current = models.BooleanField(
        default=True,
        help_text="Marks this as the current registration session"
    )

    is_completed = models.BooleanField(
        default=False,
        help_text="Marks the session as completed"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'registration_sessions'
        verbose_name = 'Registration Session'
        verbose_name_plural = 'Registration Sessions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.course_code} - {self.name}"

    def mark_completed(self):
        """
        Mark this registration session as completed.

        Completed sessions are no longer used for new registrations.
        The records remain available until the administrator
        deliberately clears the completed session.
        """

        self.is_current = False
        self.is_completed = True
        self.completed_at = timezone.now()

        self.save(
            update_fields=[
                'is_current',
                'is_completed',
                'completed_at'
            ]
        )


class Group(models.Model):
    """
    Group belonging to a specific registration session.
    """

    name = models.CharField(
        max_length=100,
        help_text="Group name, e.g. Group A"
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    session = models.ForeignKey(
        RegistrationSession,
        on_delete=models.CASCADE,
        related_name='groups'
    )

    # ---------------------------------------------------------
    # LEADER PASSWORD
    # ---------------------------------------------------------

    # Only the hashed password is stored.
    #
    # The plaintext password is generated and returned only
    # when a group is created or its password is regenerated.
    leader_password = models.CharField(
        max_length=128,
        blank=True,
        help_text="Hashed password for the group leader"
    )

    # ---------------------------------------------------------
    # GROUP CREATION
    # ---------------------------------------------------------

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_groups',
        limit_choices_to={'is_admin': True}
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = 'groups'
        verbose_name = 'Group'
        verbose_name_plural = 'Groups'
        ordering = ['name']

        constraints = [
            models.UniqueConstraint(
                fields=['session', 'name'],
                name='unique_group_name_per_session'
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.session.name})"

    # ---------------------------------------------------------
    # PASSWORD MANAGEMENT
    # ---------------------------------------------------------

    def generate_secure_password(self, length=12):
        """
        Generate a secure random password for the group leader.

        The password is never stored in plaintext.
        """

        alphabet = (
            string.ascii_letters
            + string.digits
            + "!@#$%^&*"
        )

        return ''.join(
            secrets.choice(alphabet)
            for _ in range(length)
        )

    def set_leader_password(self, raw_password=None):
        """
        Set a new leader password.

        If no password is supplied, a secure random password
        is generated.

        The plaintext password is returned to the caller once.
        Only its hash is stored in the database.
        """

        if not raw_password:
            raw_password = self.generate_secure_password()

        self.leader_password = make_password(
            raw_password
        )

        self.save(
            update_fields=[
                'leader_password',
                'updated_at'
            ]
        )

        return raw_password

    def regenerate_leader_password(self):
        """
        Generate and store a completely new leader password.

        The previous password becomes invalid immediately.

        The new plaintext password is returned only once to
        the authorized administrator.
        """

        return self.set_leader_password()

    def check_leader_password(self, raw_password):
        """
        Check whether the supplied password matches the
        stored leader password.
        """

        if not self.leader_password:
            return False

        return check_password(
            raw_password,
            self.leader_password
        )

    # ---------------------------------------------------------
    # MEMBER STATISTICS
    # ---------------------------------------------------------

    def get_member_count(self):
        """
        Get the total number of students in this group.
        """

        return self.members.count()

    def get_paid_count(self):
        """
        Get the number of students whose payment has been
        confirmed.
        """

        return self.members.filter(
            has_paid=True
        ).count()

    def get_unpaid_count(self):
        """
        Get the number of students whose payment has not
        been confirmed.
        """

        return self.members.filter(
            has_paid=False
        ).count()

    def get_payment_rate(self):
        """
        Calculate the group's payment rate as a percentage.
        """

        total = self.get_member_count()

        if total == 0:
            return 0

        paid = self.get_paid_count()

        return round(
            (paid / total) * 100,
            2
        )

    def get_members_list(self):
        """
        Return all students in this group ordered by name.
        """

        return self.members.order_by(
            'full_name'
        )

    # ---------------------------------------------------------
    # LEADER
    # ---------------------------------------------------------

    def get_leader(self):
        """
        Return the group leader assigned to this group.
        """

        return self.leaders.filter(
            is_group_leader=True
        ).first()
