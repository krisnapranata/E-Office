from django.conf import settings
from django.db import models

from accounts.files import protected_upload_to, validate_upload
from workflow.models import Priority


def notulen_upload_to(instance, filename):
    return protected_upload_to("notulen")(instance, filename)


class MeetingMinutes(models.Model):
    """Notulen satu rapat (E-Agenda jenis Rapat). Disetujui pimpinan rapat sebelum keputusan menjadi tugas."""

    class Status(models.TextChoices):
        DRAF = "DRAF", "Draf"
        DIAJUKAN = "DIAJUKAN", "Diajukan untuk persetujuan"
        DISETUJUI = "DISETUJUI", "Disetujui"

    event = models.OneToOneField("agenda.AgendaEvent", on_delete=models.PROTECT, related_name="minutes")
    attendees = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="+",
                                       verbose_name="peserta hadir")
    guests = models.CharField("peserta lain/tamu", max_length=500, blank=True)
    discussion = models.TextField("pokok pembahasan")
    summary = models.TextField("ringkasan", blank=True)
    attachment = models.FileField("lampiran notulen", upload_to=notulen_upload_to, blank=True,
                                  validators=[validate_upload])
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAF)
    revision = models.PositiveSmallIntegerField("revisi", default=0)
    return_note = models.TextField("catatan pengembalian", blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+",
                                   verbose_name="notulis")
    created_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
                                    related_name="+")
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "notulen"
        verbose_name_plural = "notulen"

    def __str__(self):
        return f"Notulen {self.event.title}"

    @property
    def editable(self):
        return self.status == self.Status.DRAF


class MeetingDecision(models.Model):
    """Butir keputusan rapat yang terstruktur (PRD 6.8)."""

    minutes = models.ForeignKey(MeetingMinutes, on_delete=models.CASCADE, related_name="decisions")
    number = models.PositiveSmallIntegerField("nomor")
    text = models.TextField("keputusan")
    requires_action = models.BooleanField("memerlukan tindakan", default=True)
    priority = models.CharField("prioritas", max_length=10, choices=Priority.choices, default=Priority.SEDANG)
    due_date = models.DateField("tenggat", null=True, blank=True)
    completion_criteria = models.TextField("kriteria selesai", blank=True)

    class Meta:
        ordering = ["number"]
        constraints = [models.UniqueConstraint(fields=["minutes", "number"], name="uniq_decision_number")]

    def __str__(self):
        return f"Keputusan {self.number}: {self.text[:60]}"


class DecisionAssignee(models.Model):
    """PIC/unit tindak lanjut sebuah keputusan. Setiap baris menjadi satu tugas saat notulen disetujui."""

    decision = models.ForeignKey(MeetingDecision, on_delete=models.CASCADE, related_name="assignees")
    unit = models.ForeignKey("accounts.OrganizationUnit", on_delete=models.PROTECT, related_name="+")
    pic = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+",
                            verbose_name="PIC")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["decision", "unit", "pic"], name="uniq_decision_assignee")]

    def __str__(self):
        return f"{self.unit.code} / {self.pic}"
