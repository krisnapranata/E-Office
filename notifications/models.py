from django.conf import settings
from django.db import models


class Notification(models.Model):
    """Notifikasi internal (kanal awal; email/WhatsApp ditambahkan setelah disetujui)."""

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    kind = models.CharField(max_length=40)
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    url = models.CharField(max_length=255, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["recipient", "read_at"])]

    def __str__(self):
        return self.title


class ReminderLog(models.Model):
    class Kind(models.TextChoices):
        BEFORE_DUE = "BEFORE_DUE", "Pengingat sebelum tenggat"
        OVERDUE = "OVERDUE", "Terlambat"
        ESCALATION = "ESCALATION", "Eskalasi"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Menunggu"
        SENT = "SENT", "Terkirim"
        FAILED = "FAILED", "Gagal"

    task = models.ForeignKey("workflow.Task", on_delete=models.CASCADE, related_name="reminders")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    days_offset = models.SmallIntegerField(help_text="Selisih hari terhadap tenggat (H-2 = 2).")
    due_date = models.DateField(help_text="Tenggat saat pengingat dibuat.")
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    channel = models.CharField(max_length=20, default="internal")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # Kunci idempotensi: pengulangan job tidak membuat pengingat ganda.
            models.UniqueConstraint(
                fields=["task", "kind", "days_offset", "due_date", "recipient", "channel"],
                name="uniq_reminder",
            )
        ]

    def __str__(self):
        return f"{self.get_kind_display()} {self.task_id} → {self.recipient}"
