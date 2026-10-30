from django import forms

from accounts.models import OrganizationUnit, User

from .models import Disposition, IncomingLetter, OutgoingLetter

DATE = forms.DateInput(attrs={"type": "date"})


class IncomingLetterForm(forms.ModelForm):
    class Meta:
        model = IncomingLetter
        fields = ["letter_number", "letter_date", "received_date", "sender", "subject", "summary",
                  "classification", "attachment"]
        widgets = {"letter_date": DATE, "received_date": DATE}


class OutgoingLetterForm(forms.ModelForm):
    class Meta:
        model = OutgoingLetter
        fields = ["letter_date", "recipient", "subject", "summary", "classification", "attachment"]
        widgets = {"letter_date": DATE}


class DispositionForm(forms.ModelForm):
    class Meta:
        model = Disposition
        fields = ["to_user", "to_unit", "directive", "priority", "due_date", "requires_action"]
        widgets = {"due_date": DATE, "directive": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["to_user"].queryset = User.objects.filter(is_active=True)
        self.fields["to_unit"].queryset = OrganizationUnit.objects.filter(is_active=True)


class LetterFilterForm(forms.Form):
    q = forms.CharField(label="Cari", required=False)
    date_from = forms.DateField(label="Diterima dari", widget=DATE, required=False)
    date_to = forms.DateField(label="s.d.", widget=DATE, required=False)
