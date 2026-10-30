from django import forms

from accounts.files import validate_upload
from accounts.models import User

from .models import AgendaEvent

DT = forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")


class EventForm(forms.ModelForm):
    class Meta:
        model = AgendaEvent
        fields = ["title", "kind", "start", "end", "location", "link", "organizer", "participants", "notes",
                  "classification"]
        widgets = {"start": DT, "end": DT, "notes": forms.Textarea(attrs={"rows": 3}),
                   "participants": forms.SelectMultiple(attrs={"size": 8})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aktif = User.objects.filter(is_active=True).order_by("first_name", "username")
        self.fields["organizer"].queryset = aktif
        self.fields["participants"].queryset = aktif
        self.fields["participants"].help_text = "Tahan Ctrl untuk memilih beberapa peserta."
        for f in ("start", "end"):
            self.fields[f].input_formats = ["%Y-%m-%dT%H:%M"]


class MaterialForm(forms.Form):
    file = forms.FileField(label="Bahan", validators=[validate_upload])
    description = forms.CharField(label="Keterangan", max_length=255, required=False)
