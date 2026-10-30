from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    action = models.CharField("aksi", max_length=50, db_index=True)
    object_type = models.CharField("jenis objek", max_length=50, db_index=True)
    object_id = models.CharField(max_length=40, db_index=True)
    object_repr = models.CharField(max_length=255)
    changes = models.JSONField("ringkasan perubahan", default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "log audit"
        verbose_name_plural = "log audit"

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.user} {self.action} {self.object_repr}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Log audit tidak boleh diubah.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Log audit tidak boleh dihapus.")
