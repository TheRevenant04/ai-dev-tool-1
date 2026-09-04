from calendar import monthrange
from datetime import timedelta
import secrets
import string

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Household(models.Model):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=8, unique=True, editable=False)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_households")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name

    @classmethod
    def new_code(cls):
        alphabet = string.ascii_uppercase + string.digits
        while True:
            code = "".join(secrets.choice(alphabet) for _ in range(8))
            if not cls.objects.filter(code=code).exists():
                return code


class Membership(models.Model):
    ADMIN = "admin"
    MEMBER = "member"
    ROLE_CHOICES = ((ADMIN, "Administrator"), (MEMBER, "Member"))

    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="household_memberships")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("joined_at", "id")
        constraints = [
            models.UniqueConstraint(fields=("household", "user"), name="unique_household_membership"),
            models.UniqueConstraint(
                fields=("household",),
                condition=Q(role="admin"),
                name="one_household_admin",
            ),
        ]

    def __str__(self):
        return f"{self.user.username} in {self.household.name}"

    @property
    def is_admin(self):
        return self.role == self.ADMIN


class Chore(models.Model):
    ONE_OFF = "one_off"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    SCHEDULE_CHOICES = (
        (ONE_OFF, "One-off"),
        (DAILY, "Daily"),
        (WEEKLY, "Weekly"),
        (MONTHLY, "Monthly"),
    )

    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="chores")
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    schedule_type = models.CharField(max_length=10, choices=SCHEDULE_CHOICES, default=ONE_OFF)
    due_date = models.DateField()
    active = models.BooleanField(default=True)
    assignee = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="base_assigned_chores"
    )
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_chores")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("due_date", "title")

    def __str__(self):
        return self.title

    def clean(self):
        if self.assignee_id and self.household_id:
            if not self.household.memberships.filter(user_id=self.assignee_id).exists():
                raise ValidationError({"assignee": "The assignee must belong to this household."})

    def is_due_on(self, on_date):
        if on_date < self.due_date:
            return False
        if self.schedule_type == self.ONE_OFF:
            return on_date == self.due_date
        if self.schedule_type == self.DAILY:
            return True
        if self.schedule_type == self.WEEKLY:
            return (on_date - self.due_date).days % 7 == 0
        target_day = min(self.due_date.day, monthrange(on_date.year, on_date.month)[1])
        return on_date.day == target_day

    def recurrence_index(self, on_date):
        if self.schedule_type == self.DAILY:
            return (on_date - self.due_date).days
        if self.schedule_type == self.WEEKLY:
            return (on_date - self.due_date).days // 7
        return (on_date.year - self.due_date.year) * 12 + on_date.month - self.due_date.month

    def scheduled_dates(self, start, end):
        current = max(start, self.due_date)
        while current <= end:
            if self.is_due_on(current):
                yield current
            if self.schedule_type == self.ONE_OFF:
                break
            current += timedelta(days=1)

    def assignment_for_date(self, on_date):
        if self.schedule_type == self.ONE_OFF:
            return self.assignee
        members = list(
            User.objects.filter(household_memberships__household=self.household)
            .order_by("household_memberships__joined_at", "id")
            .distinct()
        )
        if not members:
            return self.assignee
        return members[self.recurrence_index(on_date) % len(members)]


class ChoreOccurrence(models.Model):
    chore = models.ForeignKey(Chore, on_delete=models.CASCADE, related_name="occurrences")
    due_date = models.DateField()
    assignee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="chore_occurrences")
    completed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="completed_chore_occurrences"
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    assignment_overridden = models.BooleanField(default=False)

    class Meta:
        ordering = ("due_date", "chore__title")
        constraints = [
            models.UniqueConstraint(fields=("chore", "due_date"), name="unique_chore_occurrence"),
        ]

    def __str__(self):
        return f"{self.chore.title} on {self.due_date}"

    @property
    def is_completed(self):
        return self.completed_at is not None

    def ensure_assignment(self):
        if not self.assignment_overridden:
            assigned = self.chore.assignment_for_date(self.due_date)
            if assigned and self.assignee_id != assigned.id:
                self.assignee = assigned
                self.save(update_fields=("assignee",))
        return self

    def clean(self):
        if self.assignee_id and not self.chore.household.memberships.filter(user_id=self.assignee_id).exists():
            raise ValidationError({"assignee": "The assignee must belong to this household."})
