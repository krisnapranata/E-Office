from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from accounts.files import evidence_upload_to, validate_upload
from accounts.permissions import Classification


class Priority(models.TextChoices):
    RENDAH = "RENDAH", "Rendah"
    SEDANG = "SEDANG", "Sedang"
    TINGGI = "TINGGI", "Tinggi"
    MENDESAK = "MENDESAK", "Mendesak"


class TaskStatus(models.TextChoices):
    DRAF = "DRAF", "Draf"
    MENUNGGU_PENERIMAAN = "MENUNGGU_PENERIMAAN", "Menunggu penerimaan"
    BELUM_DIMULAI = "BELUM_DIMULAI", "Belum dimulai"
    BERJALAN = "BERJALAN", "Berjalan"
    TERHAMBAT = "TERHAMBAT", "Terhambat"
    MENUNGGU_VERIFIKASI = "MENUNGGU_VERIFIKASI", "Menunggu verifikasi"
    PERLU_PERBAIKAN = "PERLU_PERBAIKAN", "Perlu perbaikan"
    SELESAI = "SELESAI", "Selesai"
    DIBATALKAN = "DIBATALKAN", "Dibatalkan"


CLOSED_STATUSES = (TaskStatus.SELESAI, TaskStatus.DIBATALKAN)


class TaskSource(models.TextChoices):
    DISPOSISI = "DISPOSISI", "Disposisi"
    INSTRUKSI = "INSTRUKSI", "Instruksi"
    KEPUTUSAN_RAPAT = "KEPUTUSAN_RAPAT", "Keputusan rapat"
    LANGSUNG = "LANGSUNG", "Penugasan langsung"


class TaskQuerySet(models.QuerySet):
    def open(self):
        return self.exclude(status__in=CLOSED_STATUSES)

    def overdue(self, today=None):
        today = today or timezone.localdate()
        return self.open().filter(due_date__lt=today)

    def due_soon(self, today=None, days=2):
        """Tugas terbuka dengan tenggat hari ini s.d. H-`days` (belum terlambat)."""
        today = today or timezone.localdate()
        return self.open().filter(due_date__gte=today, due_date__lte=today + timedelta(days=days))


class Task(models.Model):
    """Satu model tugas menjadi pusat monitoring lintas modul (PRD Bab 12)."""

    title = models.CharField("judul", max_length=255)
    description = models.TextField("deskripsi", blank=True)
    source_type = models.CharField(
        "sumber", max_length=20, choices=TaskSource.choices, default=TaskSource.LANGSUNG
    )
    disposition = models.ForeignKey(
        "letters.Disposition", null=True, blank=True, on_delete=models.PROTECT,
        related_name="tasks",
    )
    instruction = models.ForeignKey(
        "instructions.Instruction", null=True, blank=True, on_delete=models.PROTECT,
        related_name="tasks",
    )
    decision = models.ForeignKey(
        "notulen.MeetingDecision", null=True, blank=True, on_delete=models.PROTECT,
        related_name="tasks", verbose_name="keputusan rapat",
    )
    source_note = models.CharField(
        "alasan/sumber lain", max_length=255, blank=True,
        help_text="Wajib untuk penugasan langsung.",
    )
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="subtasks"
    )
    unit = models.ForeignKey(
        "accounts.OrganizationUnit", on_delete=models.PROTECT, related_name="tasks"
    )
    pic = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="tasks_as_pic",
        verbose_name="PIC",
    )
    collaborators = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="tasks_as_collaborator",
        verbose_name="kolaborator",
    )
    priority = models.CharField(
        "prioritas", max_length=10, choices=Priority.choices, default=Priority.SEDANG
    )
    classification = models.CharField(
        "klasifikasi", max_length=10, choices=Classification.CHOICES, default=Classification.BIASA
    )
    start_date = models.DateField("tanggal mulai", null=True, blank=True)
    due_date = models.DateField("tenggat", null=True, blank=True, db_index=True)
    completion_criteria = models.TextField("kriteria selesai", blank=True)
    requires_evidence = models.BooleanField("wajib bukti", default=True)
    requires_verification = models.BooleanField("wajib verifikasi", default=True)
    verifier = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="tasks_to_verify",
        verbose_name="verifikator",
    )
    status = models.CharField(
        max_length=25, choices=TaskStatus.choices, default=TaskStatus.DRAF, db_index=True
    )
    progress = models.PositiveSmallIntegerField("progres (%)", default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="tasks_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    objects = TaskQuerySet.as_manager()

    class Meta:
        ordering = ["due_date", "-id"]
        verbose_name = "tugas"
        verbose_name_plural = "tugas"
        indexes = [models.Index(fields=["unit", "status"]), models.Index(fields=["pic", "status"])]
        constraints = [
            # Mencegah tugas ganda dari sumber yang sama. NULL tidak dianggap sama oleh
            # unique index MySQL/MariaDB, sehingga tugas tanpa sumber tersebut tidak terdampak.
            models.UniqueConstraint(
                fields=["instruction", "unit", "pic"], name="uniq_task_per_instruction_target"
            ),
            models.UniqueConstraint(fields=["disposition"], name="uniq_task_per_disposition"),
            models.UniqueConstraint(fields=["decision", "unit", "pic"], name="uniq_task_per_decision_target"),
            models.CheckConstraint(
                condition=Q(progress__lte=100), name="task_progress_lte_100"
            ),
        ]

    def __str__(self):
        return f"T-{self.pk} {self.title}"

    @property
    def is_closed(self):
        return self.status in CLOSED_STATUSES

    def days_left(self, today=None):
        if not self.due_date:
            return None
        return (self.due_date - (today or timezone.localdate())).days

    def due_label(self, today=None):
        """Keterangan sisa waktu untuk tampilan, mis. "2 hari lagi" atau "terlambat 3 hari"."""
        left = self.days_left(today)
        if left is None or self.is_closed:
            return ""
        if left < 0:
            return f"terlambat {-left} hari"
        return "hari ini" if left == 0 else f"{left} hari lagi"

    def is_overdue(self, today=None):
        left = self.days_left(today)
        return left is not None and left < 0 and not self.is_closed

    def finished_on_time(self):
        if self.status != TaskStatus.SELESAI or not self.due_date or not self.closed_at:
            return None
        return timezone.localtime(self.submitted_at or self.closed_at).date() <= self.due_date

    @property
    def source_object(self):
        return self.disposition or self.instruction or self.decision

    # Relasi yang dibutuhkan `pemberi`/`asal_singkat`; pakai di select_related agar daftar tidak N+1.
    RELASI_PEMBERI = ("created_by__unit", "disposition__from_user__unit", "disposition__letter",
                      "instruction__created_by__unit", "instruction__on_behalf_of__unit",
                      "decision__minutes__event__organizer__unit")

    @property
    def pemberi(self):
        """Orang yang SEBENARNYA memberi tugas (bukan sekadar yang mengetik): pemberi disposisi, pemberi instruksi
        (termasuk 'atas nama'), pimpinan rapat untuk keputusan rapat, atau pembuat penugasan langsung."""
        if self.disposition_id:
            return self.disposition.from_user
        if self.instruction_id:
            return self.instruction.issuer
        if self.decision_id:
            return self.decision.minutes.event.organizer
        return self.created_by

    @property
    def asal_singkat(self):
        if self.disposition_id:
            return f"Disposisi surat: {self.disposition.letter.subject}"
        if self.instruction_id:
            return f"Instruksi {self.instruction.code}: {self.instruction.title}"
        if self.decision_id:
            return f"Keputusan rapat: {self.decision.minutes.event.title}"
        return f"Penugasan langsung{': ' + self.source_note if self.source_note else ''}"


class TaskUpdate(models.Model):
    """Riwayat progres/komentar/hambatan yang dilaporkan PIC."""

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="updates")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    progress = models.PositiveSmallIntegerField(null=True, blank=True)
    status_from = models.CharField(max_length=25, blank=True)
    status_to = models.CharField(max_length=25, blank=True)
    note = models.TextField("catatan", blank=True)
    obstacle = models.TextField("hambatan", blank=True)
    decision_needed = models.TextField("keputusan yang dibutuhkan", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class TaskEvidence(models.Model):
    task = models.ForeignKey(Task, on_delete=models.PROTECT, related_name="evidences")
    file = models.FileField(upload_to=evidence_upload_to, validators=[validate_upload])
    original_name = models.CharField(max_length=255)
    description = models.CharField("keterangan", max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.original_name


class TaskVerification(models.Model):
    class Decision(models.TextChoices):
        DISETUJUI = "DISETUJUI", "Disetujui"
        PERLU_PERBAIKAN = "PERLU_PERBAIKAN", "Perlu perbaikan"

    task = models.ForeignKey(Task, on_delete=models.PROTECT, related_name="verifications")
    verifier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    decision = models.CharField(max_length=20, choices=Decision.choices)
    note = models.TextField("catatan", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
