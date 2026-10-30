from django.contrib.auth.models import AbstractUser
from django.db import models


class OrganizationUnit(models.Model):
    code = models.CharField("kode", max_length=20, unique=True)
    name = models.CharField("nama", max_length=150)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    head = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="headed_units",
        verbose_name="kepala unit",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        verbose_name = "unit kerja"
        verbose_name_plural = "unit kerja"

    def __str__(self):
        return f"{self.code} — {self.name}"

    def descendant_ids(self):
        """ID unit ini beserta seluruh sub-unitnya."""
        ids, frontier = {self.pk}, [self.pk]
        while frontier:
            frontier = list(
                OrganizationUnit.objects.filter(parent_id__in=frontier)
                .exclude(pk__in=ids)
                .values_list("pk", flat=True)
            )
            ids.update(frontier)
        return ids


class Role(models.TextChoices):
    DIREKTUR = "DIREKTUR", "Direktur"
    WADIR = "WADIR", "Wakil Direktur/Manajer"
    KEPALA_UNIT = "KEPALA_UNIT", "Kepala Unit/Instalasi"
    STAF = "STAF", "Staf/PIC"
    SEKRETARIS = "SEKRETARIS", "Sekretaris/Admin Direktur"
    ARSIP = "ARSIP", "Petugas Arsip"
    ADMIN = "ADMIN", "Administrator Sistem"
    AUDITOR = "AUDITOR", "Auditor/Reviewer"


class User(AbstractUser):
    role = models.CharField("peran", max_length=20, choices=Role.choices, default=Role.STAF)
    unit = models.ForeignKey(
        OrganizationUnit,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="members",
        verbose_name="unit kerja",
    )
    supervisor = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="subordinates",
        verbose_name="atasan langsung",
        help_text="Penerima eskalasi keterlambatan.",
    )
    position = models.CharField("jabatan", max_length=150, blank=True)

    class Meta:
        verbose_name = "pengguna"
        verbose_name_plural = "pengguna"

    def __str__(self):
        return self.get_full_name() or self.username
