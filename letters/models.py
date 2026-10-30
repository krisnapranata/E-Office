from django.conf import settings
from django.db import models

from accounts.files import letter_upload_to, validate_upload
from accounts.permissions import Classification
from workflow.models import Priority


class IncomingLetter(models.Model):
    agenda_number = models.CharField("nomor agenda", max_length=30, unique=True, editable=False)
    letter_number = models.CharField("nomor surat", max_length=100)
    letter_date = models.DateField("tanggal surat")
    received_date = models.DateField("tanggal diterima")
    sender = models.CharField("pengirim", max_length=200)
    subject = models.CharField("perihal", max_length=255)
    summary = models.TextField("ringkasan", blank=True)
    classification = models.CharField(
        "klasifikasi", max_length=10, choices=Classification.CHOICES, default=Classification.BIASA
    )
    attachment = models.FileField(
        "lampiran", upload_to=letter_upload_to, blank=True, validators=[validate_upload]
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_date", "-id"]
        verbose_name = "surat masuk"
        verbose_name_plural = "surat masuk"

    def __str__(self):
        return f"{self.agenda_number} — {self.subject}"


class OutgoingLetter(models.Model):
    letter_number = models.CharField("nomor surat", max_length=30, unique=True, editable=False)
    letter_date = models.DateField("tanggal surat")
    recipient = models.CharField("penerima", max_length=200)
    subject = models.CharField("perihal", max_length=255)
    summary = models.TextField("ringkasan", blank=True)
    classification = models.CharField(
        "klasifikasi", max_length=10, choices=Classification.CHOICES, default=Classification.BIASA
    )
    attachment = models.FileField(
        "lampiran", upload_to=letter_upload_to, blank=True, validators=[validate_upload]
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-letter_date", "-id"]
        verbose_name = "surat keluar"
        verbose_name_plural = "surat keluar"

    def __str__(self):
        return f"{self.letter_number} — {self.subject}"


class Disposition(models.Model):
    class Status(models.TextChoices):
        TERKIRIM = "TERKIRIM", "Terkirim"
        DIBACA = "DIBACA", "Dibaca"
        DITINDAKLANJUTI = "DITINDAKLANJUTI", "Ditindaklanjuti"
        SELESAI = "SELESAI", "Selesai"

    letter = models.ForeignKey(
        IncomingLetter, on_delete=models.PROTECT, related_name="dispositions"
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="forwards",
        help_text="Disposisi asal bila ini merupakan penerusan.",
    )
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="dispositions_sent"
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="dispositions_received",
        verbose_name="penerima",
    )
    to_unit = models.ForeignKey(
        "accounts.OrganizationUnit", on_delete=models.PROTECT, related_name="+",
        verbose_name="unit",
    )
    directive = models.TextField("arahan")
    priority = models.CharField(
        "prioritas", max_length=10, choices=Priority.choices, default=Priority.SEDANG
    )
    due_date = models.DateField("tenggat", null=True, blank=True)
    requires_action = models.BooleanField(
        "memerlukan tindakan", default=True,
        help_text="Jika ya, sistem membuat tugas tertaut untuk penerima.",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TERKIRIM)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "disposisi"
        verbose_name_plural = "disposisi"

    def __str__(self):
        return f"Disposisi #{self.pk} {self.letter.agenda_number} → {self.to_user}"
