from django import forms

from accounts.files import validate_upload
from accounts.models import OrganizationUnit

from .models import ArchiveDocument

DATE = forms.DateInput(attrs={"type": "date"})


class ArchiveForm(forms.ModelForm):
    file = forms.FileField(label="Berkas", validators=[validate_upload])

    class Meta:
        model = ArchiveDocument
        fields = ["doc_type", "number", "doc_date", "title", "unit", "classification", "keywords"]
        widgets = {"doc_date": DATE}


class MetadataForm(forms.ModelForm):
    class Meta:
        model = ArchiveDocument
        fields = ["number", "doc_date", "title", "unit", "classification", "keywords"]
        widgets = {"doc_date": DATE}


class VersionForm(forms.Form):
    file = forms.FileField(label="Berkas revisi", validators=[validate_upload])
    note = forms.CharField(label="Catatan versi (alasan revisi)", max_length=255)


class ArchiveFilterForm(forms.Form):
    q = forms.CharField(label="Cari", required=False, help_text="Judul, nomor, atau kata kunci")
    doc_type = forms.ChoiceField(label="Jenis", required=False,
                                 choices=[("", "Semua jenis")] + ArchiveDocument.DocType.choices)
    unit = forms.ModelChoiceField(label="Unit", queryset=OrganizationUnit.objects.all(), required=False,
                                  empty_label="Semua unit")
    tahun = forms.IntegerField(label="Tahun", required=False, min_value=2000, max_value=2100)
    status = forms.ChoiceField(label="Status", required=False,
                               choices=[("", "Semua status"), ("RETENSI", "Lewat masa retensi")]
                               + ArchiveDocument.Status.choices)
