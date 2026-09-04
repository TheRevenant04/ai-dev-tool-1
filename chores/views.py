from collections import OrderedDict
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import AssignmentForm, ChoreForm, HouseholdForm, JoinHouseholdForm, RegistrationForm
from .models import Chore, ChoreOccurrence, Household, Membership
from .services import household_occurrences, occurrence_for


def home(request):
    return render(request, "chores/home.html")


def health_check(request):
    return JsonResponse({"status": "ok"})


class UserLoginView(LoginView):
    template_name = "registration/login.html"
    next_page = reverse_lazy("dashboard")


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegistrationForm(request.POST or None)
    if form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Your account is ready. Create or join a household.")
        return redirect("household-create")
    return render(request, "registration/register.html", {"form": form})


@login_required
def logout_view(request):
    logout(request)
    return redirect("home")


@login_required
def dashboard(request):
    membership = Membership.objects.filter(user=request.user).select_related("household").first()
    if not membership:
        return redirect("household-create")
    today = timezone.localdate()
    occurrences = household_occurrences(membership.household)
    grouped = OrderedDict()
    for occurrence in occurrences:
        grouped.setdefault(occurrence.due_date, []).append(occurrence)
    reminders = [
        occurrence
        for occurrence in occurrences
        if not occurrence.is_completed
        and (occurrence.due_date < today or occurrence.due_date <= today + timedelta(days=2))
    ]
    return render(
        request,
        "chores/dashboard.html",
        {
            "membership": membership,
            "household": membership.household,
            "grouped_occurrences": grouped.items(),
            "reminders": reminders,
            "today": today,
        },
    )


@login_required
def household_create(request):
    if Membership.objects.filter(user=request.user).exists():
        return redirect("dashboard")
    form = HouseholdForm(request.POST or None)
    if form.is_valid():
        with transaction.atomic():
            household = form.save(commit=False)
            household.created_by = request.user
            household.code = Household.new_code()
            household.save()
            Membership.objects.create(household=household, user=request.user, role=Membership.ADMIN)
        messages.success(request, f"Household created. Share code {household.code} with your household.")
        return redirect("dashboard")
    return render(request, "chores/household_form.html", {"form": form, "heading": "Create a household"})


@login_required
def household_join(request):
    if Membership.objects.filter(user=request.user).exists():
        return redirect("dashboard")
    form = JoinHouseholdForm(request.POST or None)
    if form.is_valid():
        household = form.household
        Membership.objects.create(household=household, user=request.user, role=Membership.MEMBER)
        messages.success(request, f"You joined {household.name}.")
        return redirect("dashboard")
    return render(request, "chores/household_join.html", {"form": form})


def _membership(request, household):
    return Membership.objects.filter(user=request.user, household=household).first()


def _admin_required(request, household):
    membership = _membership(request, household)
    if not membership or not membership.is_admin:
        return None
    return membership


@login_required
def chore_create(request):
    membership = Membership.objects.filter(user=request.user).select_related("household").first()
    if not membership:
        return redirect("household-create")
    if not membership.is_admin:
        return HttpResponseForbidden("Only household administrators can manage chores.")
    form = ChoreForm(request.POST or None, household=membership.household)
    if form.is_valid():
        chore = form.save(commit=False)
        chore.household = membership.household
        chore.created_by = request.user
        chore.save()
        messages.success(request, "Chore created.")
        return redirect("dashboard")
    return render(request, "chores/chore_form.html", {"form": form, "heading": "Add chore"})


@login_required
def chore_edit(request, pk):
    chore = get_object_or_404(Chore, pk=pk)
    if not _admin_required(request, chore.household):
        return HttpResponseForbidden("Only household administrators can manage chores.")
    form = ChoreForm(request.POST or None, instance=chore, household=chore.household)
    if form.is_valid():
        form.save()
        messages.success(request, "Chore updated.")
        return redirect("dashboard")
    return render(request, "chores/chore_form.html", {"form": form, "heading": "Edit chore", "chore": chore})


@login_required
def chore_delete(request, pk):
    chore = get_object_or_404(Chore, pk=pk)
    if not _admin_required(request, chore.household):
        return HttpResponseForbidden("Only household administrators can manage chores.")
    if request.method == "POST":
        chore.delete()
        messages.success(request, "Chore deleted.")
        return redirect("dashboard")
    return render(request, "chores/chore_confirm_delete.html", {"chore": chore})


@login_required
def occurrence_override(request, chore_id, due_date):
    chore = get_object_or_404(Chore, pk=chore_id)
    if not _admin_required(request, chore.household):
        return HttpResponseForbidden("Only household administrators can override assignments.")
    try:
        parsed_date = date.fromisoformat(due_date)
    except ValueError:
        return HttpResponseForbidden("Invalid occurrence date.")
    if not chore.is_due_on(parsed_date):
        return HttpResponseForbidden("That date is not an occurrence for this chore.")
    occurrence = occurrence_for(chore, parsed_date)
    form = AssignmentForm(request.POST or None, household=chore.household, initial={"assignee": occurrence.assignee})
    if form.is_valid():
        occurrence.assignee = form.cleaned_data["assignee"]
        occurrence.assignment_overridden = True
        occurrence.save(update_fields=("assignee", "assignment_overridden"))
        messages.success(request, "Assignment updated for this occurrence.")
        return redirect("dashboard")
    return render(
        request,
        "chores/occurrence_override.html",
        {"form": form, "occurrence": occurrence, "chore": chore},
    )


@require_POST
@login_required
def occurrence_complete(request, occurrence_id):
    occurrence = get_object_or_404(
        ChoreOccurrence.objects.select_related("chore", "assignee"),
        pk=occurrence_id,
    )
    membership = _membership(request, occurrence.chore.household)
    if not membership or (not membership.is_admin and occurrence.assignee_id != request.user.id):
        return HttpResponseForbidden("Only the assigned member or administrator can complete this chore.")
    if not occurrence.completed_at:
        occurrence.completed_by = request.user
        occurrence.completed_at = timezone.now()
        occurrence.save(update_fields=("completed_by", "completed_at"))
        messages.success(request, f"{occurrence.chore.title} marked complete.")
    return redirect("dashboard")
