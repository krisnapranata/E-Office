from django import forms

from accounts.models import OrganizationUnit, User

from .models import MeetingDecision, MeetingMinutes

DATE = forms.DateInput(attrs={"type": "date"})


class MinutesForm(forms.ModelForm):
    class Meta:
        model = MeetingMinutes
        fields = ["attendees", "guests", "discussion", "summary", "attachment"]
        widgets = {"discussion": forms.Textarea(attrs={"rows": 6}), "summary": forms.Textarea(attrs={"rows": 3}),
                   "attendees": forms.SelectMultiple(attrs={"size": 8})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["attendees"].queryset = User.objects.filter(is_active=True).order_by("first_name", "username")
        self.fields["attendees"].help_text = "Tahan Ctrl untuk memilih beberapa peserta."


class DecisionForm(forms.ModelForm):
    class Meta:
        model = MeetingDecision
        fields = ["text", "requires_action", "priority", "due_date", "completion_criteria"]
        widgets = {"text": forms.Textarea(attrs={"rows": 2}), "due_date": DATE,
                   "completion_criteria": forms.Textarea(attrs={"rows": 2})}


class AssigneeForm(forms.Form):
    unit = forms.ModelChoiceField(queryset=OrganizationUnit.objects.filter(is_active=True))
    pic = forms.ModelChoiceField(label="PIC", queryset=User.objects.filter(is_active=True))
