from django import forms

from accounts.models import OrganizationUnit, User
from accounts.files import validate_upload

from .models import Priority, Task, TaskSource, TaskStatus
from .services import PROGRESS_STATUSES

DATE = forms.DateInput(attrs={"type": "date"})


class DirectTaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "description", "source_note", "unit", "pic", "collaborators",
                  "priority", "classification", "start_date", "due_date",
                  "completion_criteria", "requires_evidence", "requires_verification"]
        widgets = {"start_date": DATE, "due_date": DATE}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["source_note"].required = True
        self.fields["due_date"].required = True
        self.fields["unit"].queryset = OrganizationUnit.objects.filter(is_active=True)
        self.fields["pic"].queryset = User.objects.filter(is_active=True)


class ProgressForm(forms.Form):
    progress = forms.IntegerField(label="Progres (%)", min_value=0, max_value=100)
    status = forms.ChoiceField(choices=[(s.value, s.label) for s in PROGRESS_STATUSES])
    note = forms.CharField(label="Catatan", widget=forms.Textarea(attrs={"rows": 2}), required=False)
    obstacle = forms.CharField(label="Hambatan", widget=forms.Textarea(attrs={"rows": 2}),
                               required=False)
    decision_needed = forms.CharField(label="Keputusan yang dibutuhkan", required=False,
                                      widget=forms.Textarea(attrs={"rows": 2}))


class EvidenceForm(forms.Form):
    file = forms.FileField(label="Berkas bukti", validators=[validate_upload])
    description = forms.CharField(label="Keterangan", max_length=255, required=False)


class VerifyForm(forms.Form):
    decision = forms.ChoiceField(choices=[("approve", "Setujui & tutup"),
                                          ("revise", "Kembalikan untuk perbaikan")])
    note = forms.CharField(label="Catatan/alasan", widget=forms.Textarea(attrs={"rows": 2}),
                           required=False)


class ReassignForm(forms.Form):
    pic = forms.ModelChoiceField(label="PIC baru", queryset=User.objects.filter(is_active=True),
                                 required=False)
    due_date = forms.DateField(label="Tenggat baru", widget=DATE, required=False)
    reason = forms.CharField(label="Alasan perubahan", widget=forms.Textarea(attrs={"rows": 2}))


class ReasonForm(forms.Form):
    reason = forms.CharField(label="Alasan", widget=forms.Textarea(attrs={"rows": 2}))


class TaskFilterForm(forms.Form):
    FLAG_CHOICES = [("", "Semua"), ("overdue", "Terlambat"), ("due_soon", "Tenggat ≤ H-2"),
                    ("open", "Belum ditutup")]
    q = forms.CharField(label="Cari", required=False)
    status = forms.ChoiceField(label="Status", required=False,
                               choices=[("", "Semua status")] + TaskStatus.choices)
    flag = forms.ChoiceField(label="Penanda", choices=FLAG_CHOICES, required=False)
    source_type = forms.ChoiceField(label="Sumber", required=False,
                                    choices=[("", "Semua sumber")] + TaskSource.choices)
    priority = forms.ChoiceField(label="Prioritas", required=False,
                                 choices=[("", "Semua prioritas")] + Priority.choices)
    unit = forms.ModelChoiceField(label="Unit", queryset=OrganizationUnit.objects.all(),
                                  required=False, empty_label="Semua unit")
    pic = forms.ModelChoiceField(label="PIC", queryset=User.objects.filter(is_active=True),
                                 required=False, empty_label="Semua PIC")
    due_from = forms.DateField(label="Tenggat dari", widget=DATE, required=False)
    due_to = forms.DateField(label="Tenggat s.d.", widget=DATE, required=False)
