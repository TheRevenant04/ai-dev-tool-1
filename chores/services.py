from datetime import timedelta

from django.utils import timezone

from .models import ChoreOccurrence


def occurrence_for(chore, due_date):
    occurrence, _ = ChoreOccurrence.objects.get_or_create(
        chore=chore,
        due_date=due_date,
        defaults={"assignee": chore.assignment_for_date(due_date)},
    )
    return occurrence.ensure_assignment()


def household_occurrences(household, start=None, end=None):
    start = start or (timezone.localdate() - timedelta(days=7))
    end = end or (timezone.localdate() + timedelta(days=30))
    occurrences = []
    for chore in household.chores.filter(active=True).select_related("assignee"):
        for due_date in chore.scheduled_dates(start, end):
            occurrences.append(occurrence_for(chore, due_date))
    return sorted(occurrences, key=lambda item: (item.due_date, item.chore.title.lower()))
