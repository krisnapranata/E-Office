from django.conf import settings
from django.db import models

from accounts.files import instruction_upload_to, validate_upload
from accounts.permissions import Classification
from workflow.models import Priority


class Instruction(models.Model):
    class Status(models.TextChoices):
        DRAF = "DRAF", "Draf"
        DITERBITKAN = "DITERBITKAN", "Diterbitkan"
        DIBATALKAN = "DIBATALKAN", "Dibatalkan"

    code = models.CharField("kode", max_length=30, unique=True, editable=False)
    title = models.CharField("judul", max_length=255)
    description = models.TextField("uraian")
    instruction_date = models.DateField("tanggal instruksi")
    priority = models.CharField(
        "prioritas", max_length=10, choices=Priority.choices, default=Priority.SEDANG
    )
    classification = models.CharField(
        "klasifikasi", max_length=10, choices=Classification.CHOICES, default=Classification.BIASA
    )
    due_date = models.DateField("tenggat", null=True, blank=True)
    completion_criteria = models.TextField("kriteria selesai", blank=True)
    requires_evidence = models.BooleanField("wajib bukti", default=True)
    requires_verification = models.BooleanField("wajib verifikasi", default=True)
    attachment = models.FileField(
        "lampiran", upload_to=instruction_upload_to, blank=True, validators=[validate_upload]
    )
    on_behalf_of = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
        related_name="+", verbose_name="atas nama",
        help_text="Diisi bila sekretariat mencatat instruksi atas nama pimpinan.",
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.DRAF)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="instructions_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    issued_at = models.DateTimeField(null=True, blank=True)
    cancelled_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "instruksi"
        verbose_name_plural = "instruksi"

    def __str__(self):
        return f"{self.code} — {self.title}"

    @property
    def issuer(self):
        return self.on_behalf_of or self.created_by


class InstructionTarget(models.Model):
    """Penerima instruksi. Setiap target menghasilkan satu tugas untuk PIC-nya."""

    instruction = models.ForeignKey(Instruction, on_delete=models.CASCADE, related_name="targets")
    unit = models.ForeignKey("accounts.OrganizationUnit", on_delete=models.PROTECT, related_name="+")
    pic = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="instruction_targets",
        verbose_name="PIC",
    )
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["instruction", "unit", "pic"], name="uniq_instruction_target")
        ]

    def __str__(self):
        return f"{self.unit.code} / {self.pic}"
