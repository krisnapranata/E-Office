from django import forms

from accounts.models import OrganizationUnit, User
from pengaturan import aturan

from .models import Instruction

DATE = forms.DateInput(attrs={"type": "date"})


class InstructionForm(forms.ModelForm):
    class Meta:
        model = Instruction
        fields = ["title", "description", "instruction_date", "priority", "classification",
                  "due_date", "completion_criteria", "requires_evidence",
                  "requires_verification", "on_behalf_of", "attachment"]
        widgets = {"instruction_date": DATE, "due_date": DATE,
                   "description": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["on_behalf_of"].queryset = User.objects.filter(
            is_active=True, role__in=["DIREKTUR", "WADIR"])


class TargetForm(forms.Form):
    unit = forms.ModelChoiceField(queryset=OrganizationUnit.objects.filter(is_active=True))
    pic = forms.ModelChoiceField(label="PIC", queryset=User.objects.filter(is_active=True))

    def __init__(self, *args, pemberi=None, **kwargs):
        """`pemberi` = pemberi instruksi (pihak atas nama), untuk aturan "tugas hanya ke bawahan"."""
        super().__init__(*args, **kwargs)
        aturan.saring_field(self.fields["unit"], pemberi, "unit")
        aturan.saring_field(self.fields["pic"], pemberi)
