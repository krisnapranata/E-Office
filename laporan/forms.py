from django import forms
from django.utils import timezone

from accounts.models import OrganizationUnit, User
from workflow.models import TaskSource, TaskStatus

DATE = forms.DateInput(attrs={"type": "date"})


class ReportForm(forms.Form):
    dari = forms.DateField(label="Dari tanggal", widget=DATE)
    sampai = forms.DateField(label="Sampai tanggal", widget=DATE)
    unit = forms.ModelChoiceField(label="Unit", queryset=OrganizationUnit.objects.filter(is_active=True),
                                  required=False, empty_label="Semua unit")
    pic = forms.ModelChoiceField(label="PIC", queryset=User.objects.filter(is_active=True), required=False,
                                 empty_label="Semua PIC")
    sumber = forms.ChoiceField(label="Jenis pekerjaan", required=False,
                               choices=[("", "Semua jenis")] + TaskSource.choices)
    status = forms.ChoiceField(label="Status", required=False, choices=[("", "Semua status")] + TaskStatus.choices)

    @classmethod
    def default(cls, data):
        today = timezone.localdate()
        awal = {"dari": today.replace(day=1).isoformat(), "sampai": today.isoformat()}
        return cls({**awal, **{k: v for k, v in data.items() if v}})

    def clean(self):
        d = super().clean()
        if d.get("dari") and d.get("sampai") and d["dari"] > d["sampai"]:
            raise forms.ValidationError("Tanggal awal harus sebelum tanggal akhir.")
        return d
