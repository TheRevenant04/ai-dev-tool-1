from django.contrib import admin

from .models import Chore, ChoreOccurrence, Household, Membership


@admin.register(Household)
class HouseholdAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "created_by", "created_at")
    search_fields = ("name", "code")


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("household", "user", "role", "joined_at")
    list_filter = ("role", "household")


@admin.register(Chore)
class ChoreAdmin(admin.ModelAdmin):
    list_display = ("title", "household", "schedule_type", "due_date", "active", "assignee")
    list_filter = ("schedule_type", "active", "household")
    search_fields = ("title", "description")


@admin.register(ChoreOccurrence)
class ChoreOccurrenceAdmin(admin.ModelAdmin):
    list_display = ("chore", "due_date", "assignee", "completed_by", "completed_at", "assignment_overridden")
    list_filter = ("assignment_overridden", "completed_at")
