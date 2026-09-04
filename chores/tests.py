from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Chore, ChoreOccurrence, Household, Membership
from .services import occurrence_for


class ApplicationHealthTests(TestCase):
    def test_home_page_loads(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Household chores")

    def test_health_check_returns_ok(self):
        response = self.client.get(reverse("health-check"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


class HouseholdWorkflowTests(TestCase):
    def test_registration_creates_authenticated_user(self):
        response = self.client.post(
            reverse("register"),
            {"username": "newperson", "email": "new@example.com", "password1": "SafePass123!", "password2": "SafePass123!"},
        )
        self.assertRedirects(response, reverse("household-create"))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_create_and_join_household(self):
        owner = User.objects.create_user("owner", password="SafePass123!")
        self.client.force_login(owner)
        self.client.post(reverse("household-create"), {"name": "Maple House"})
        household = Household.objects.get(name="Maple House")
        self.assertEqual(household.memberships.get().role, Membership.ADMIN)

        guest = User.objects.create_user("guest", password="SafePass123!")
        self.client.force_login(guest)
        response = self.client.post(reverse("household-join"), {"code": household.code.lower()})
        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(household.memberships.get(user=guest).role, Membership.MEMBER)

    def test_protected_dashboard_redirects_to_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('dashboard')}")


class ChorePermissionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin", password="SafePass123!")
        self.member = User.objects.create_user("member", password="SafePass123!")
        self.other = User.objects.create_user("other", password="SafePass123!")
        self.household = Household.objects.create(name="Home", code="ABCDEFGH", created_by=self.admin)
        Membership.objects.create(household=self.household, user=self.admin, role=Membership.ADMIN)
        Membership.objects.create(household=self.household, user=self.member, role=Membership.MEMBER)
        self.today = timezone.localdate()
        self.chore = Chore.objects.create(
            household=self.household,
            title="Dishes",
            schedule_type=Chore.ONE_OFF,
            due_date=self.today,
            created_by=self.admin,
            assignee=self.member,
        )

    def test_member_cannot_manage_chores(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("chore-create"))
        self.assertEqual(response.status_code, 403)
        response = self.client.get(reverse("chore-edit", args=[self.chore.pk]))
        self.assertEqual(response.status_code, 403)

    def test_household_isolation(self):
        other_house = Household.objects.create(name="Other", code="IJKLMNOP", created_by=self.other)
        Membership.objects.create(household=other_house, user=self.other, role=Membership.ADMIN)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("chore-edit", args=[self.chore.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("occurrence-override", args=[self.chore.pk, self.today])).status_code, 403)

    def test_admin_can_create_edit_and_delete(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("chore-create"),
            {"title": "Laundry", "description": "", "schedule_type": Chore.WEEKLY, "due_date": self.today, "active": "on", "assignee": self.member.pk},
        )
        self.assertRedirects(response, reverse("dashboard"))
        laundry = Chore.objects.get(title="Laundry")
        self.client.post(
            reverse("chore-edit", args=[laundry.pk]),
            {"title": "Laundry room", "description": "", "schedule_type": Chore.WEEKLY, "due_date": self.today, "active": "on", "assignee": self.member.pk},
        )
        self.assertEqual(Chore.objects.get(pk=laundry.pk).title, "Laundry room")
        self.assertEqual(self.client.post(reverse("chore-delete", args=[laundry.pk])).status_code, 302)


class RotationAndCompletionTests(TestCase):
    def setUp(self):
        self.first = User.objects.create_user("first", password="SafePass123!")
        self.second = User.objects.create_user("second", password="SafePass123!")
        self.household = Household.objects.create(name="Rotation home", code="QRSTUVWX", created_by=self.first)
        Membership.objects.create(household=self.household, user=self.first, role=Membership.ADMIN)
        Membership.objects.create(household=self.household, user=self.second, role=Membership.MEMBER)
        self.start = timezone.localdate()
        self.chore = Chore.objects.create(
            household=self.household,
            title="Bins",
            schedule_type=Chore.DAILY,
            due_date=self.start,
            created_by=self.first,
        )

    def test_recurring_assignments_rotate_deterministically(self):
        today = occurrence_for(self.chore, self.start)
        tomorrow = occurrence_for(self.chore, self.start + timedelta(days=1))
        next_day = occurrence_for(self.chore, self.start + timedelta(days=2))
        self.assertEqual([today.assignee, tomorrow.assignee, next_day.assignee], [self.first, self.second, self.first])
        self.assertEqual(occurrence_for(self.chore, self.start + timedelta(days=1)).assignee, self.second)

    def test_admin_can_override_one_occurrence(self):
        self.client.force_login(self.first)
        due = self.start + timedelta(days=1)
        response = self.client.post(
            reverse("occurrence-override", args=[self.chore.pk, due]),
            {"assignee": self.first.pk},
        )
        self.assertRedirects(response, reverse("dashboard"))
        occurrence = ChoreOccurrence.objects.get(chore=self.chore, due_date=due)
        self.assertEqual(occurrence.assignee, self.first)
        self.assertTrue(occurrence.assignment_overridden)

    def test_only_assignee_or_admin_can_complete(self):
        occurrence = occurrence_for(self.chore, self.start)
        self.client.force_login(self.second)
        self.assertEqual(self.client.post(reverse("occurrence-complete", args=[occurrence.pk])).status_code, 403)
        self.client.force_login(self.first)
        self.assertRedirects(
            self.client.post(reverse("occurrence-complete", args=[occurrence.pk])),
            reverse("dashboard"),
        )
        occurrence.refresh_from_db()
        self.assertEqual(occurrence.completed_by, self.first)
        self.assertIsNotNone(occurrence.completed_at)

    def test_dashboard_groups_dates_and_shows_reminders(self):
        self.client.force_login(self.first)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bins")
        self.assertContains(response, "Reminders")
