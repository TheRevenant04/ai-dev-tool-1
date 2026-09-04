from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Chore, Household, Membership


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=False)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


class HouseholdForm(forms.ModelForm):
    class Meta:
        model = Household
        fields = ("name",)


class JoinHouseholdForm(forms.Form):
    code = forms.CharField(max_length=8, min_length=8, strip=True, label="Household code")

    def clean_code(self):
        code = self.cleaned_data["code"].upper()
        try:
            household = Household.objects.get(code=code)
        except Household.DoesNotExist:
            raise forms.ValidationError("No household was found with that code.")
        self.household = household
        return code


class ChoreForm(forms.ModelForm):
    class Meta:
        model = Chore
        fields = ("title", "description", "schedule_type", "due_date", "active", "assignee")
        widgets = {"due_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, household=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.household = household or getattr(self.instance, "household", None)
        if self.household:
            self.fields["assignee"].queryset = User.objects.filter(
                household_memberships__household=self.household
            ).order_by("username")
        else:
            self.fields["assignee"].queryset = User.objects.none()

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("schedule_type") == Chore.ONE_OFF and not cleaned.get("due_date"):
            self.add_error("due_date", "One-off chores need a due date.")
        return cleaned


class AssignmentForm(forms.Form):
    assignee = forms.ModelChoiceField(queryset=User.objects.none(), empty_label="Unassigned")

    def __init__(self, *args, household=None, **kwargs):
        super().__init__(*args, **kwargs)
        if household:
            self.fields["assignee"].queryset = User.objects.filter(
                household_memberships__household=household
            ).order_by("username")
