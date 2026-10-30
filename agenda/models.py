from django.conf import settings
from django.db import models
from django.utils import timezone

from accounts.files import protected_upload_to, validate_upload
from accounts.permissions import Classification


def materi_upload_to(instance, filename):
    return protected_upload_to("agenda")(instance, filename)


class AgendaEvent(models.Model):
    class Kind(models.TextChoices):
        RAPAT = "RAPAT", "Rapat"
        KEGIATAN = "KEGIATAN", "Kegiatan"
        KUNJUNGAN = "KUNJUNGAN", "Kunjungan/tamu"
        LAINNYA = "LAINNYA", "Lainnya"

    class Status(models.TextChoices):
        TERJADWAL = "TERJADWAL", "Terjadwal"
        SELESAI = "SELESAI", "Selesai"
        DIBATALKAN = "DIBATALKAN", "Dibatalkan"

    title = models.CharField("judul", max_length=255)
    kind = models.CharField("jenis", max_length=12, choices=Kind.choices, default=Kind.RAPAT)
    start = models.DateTimeField("mulai", db_index=True)
    end = models.DateTimeField("selesai", null=True, blank=True)
    location = models.CharField("lokasi", max_length=255, blank=True)
    link = models.URLField("tautan rapat daring", blank=True)
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="agenda_organized",
        verbose_name="pimpinan/penyelenggara",
        help_text="Pimpinan rapat; menyetujui notulen dan memeriksa tindak lanjut keputusan.",
    )
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="agenda_invited", verbose_name="peserta"
    )
    notes = models.TextField("catatan/agenda acara", blank=True)
    classification = models.CharField(
        "klasifikasi", max_length=10, choices=Classification.CHOICES, default=Classification.BIASA
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.TERJADWAL)
    cancelled_reason = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start"]
        verbose_name = "agenda"
        verbose_name_plural = "agenda"

    def __str__(self):
        return f"{timezone.localtime(self.start):%d-%m-%Y %H:%M} {self.title}"

    @property
    def is_meeting(self):
        return self.kind == self.Kind.RAPAT


class AgendaMaterial(models.Model):
    """Bahan rapat/kegiatan; akses mengikuti hak lihat agenda."""

    event = models.ForeignKey(AgendaEvent, on_delete=models.PROTECT, related_name="materials")
    file = models.FileField(upload_to=materi_upload_to, validators=[validate_upload])
    original_name = models.CharField(max_length=255)
    description = models.CharField("keterangan", max_length=255, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["uploaded_at"]

    def __str__(self):
        return self.original_name


class AgendaReminderLog(models.Model):
    """Kunci idempotensi pengingat agenda (H-n sebelum kegiatan)."""

    event = models.ForeignKey(AgendaEvent, on_delete=models.CASCADE, related_name="reminders")
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    days_offset = models.SmallIntegerField()
    start_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["event", "recipient", "days_offset", "start_date"],
                                               name="uniq_agenda_reminder")]
