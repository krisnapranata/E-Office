from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class OrganizationUnit(models.Model):
    """Unit/jabatan organisasi. `parent` = hubungan STRUKTURAL (garis komando; dasar lingkup akses atasan dan
    eskalasi). Hubungan koordinasi/pengawasan non-struktural (SPI, komite) disimpan di `OrganizationRelation`."""

    class Kind(models.TextChoices):
        DIREKSI = "DIREKSI", "Direksi/Pimpinan"
        PENGAWAS = "PENGAWAS", "Satuan pengawas"
        KOMITE = "KOMITE", "Komite"
        BIDANG = "BIDANG", "Bidang"
        MANAJER = "MANAJER", "Manajer"
        SEKSI = "SEKSI", "Seksi"
        INSTALASI = "INSTALASI", "Instalasi"
        SUBUNIT = "SUBUNIT", "Sub-unit/urusan"
        UNIT = "UNIT", "Unit lainnya"

    code = models.CharField("kode", max_length=20, unique=True)
    name = models.CharField("nama", max_length=150)
    kind = models.CharField("jenis unit", max_length=10, choices=Kind.choices, default=Kind.UNIT)
    order = models.PositiveSmallIntegerField("urutan tampil", default=0)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children",
        verbose_name="induk struktural",
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

    def clean(self):
        # Hierarki struktural tidak boleh melingkar: induk bukan diri sendiri dan bukan salah satu sub-unitnya.
        if self.parent_id and self.pk and self.parent_id in self.descendant_ids():
            raise ValidationError({"parent": "Induk tidak boleh unit ini sendiri atau salah satu sub-unitnya."})

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


class OrganizationRelation(models.Model):
    """Hubungan NON-struktural antar-unit (garis putus-putus pada bagan), mis. komite → Direktur.
    Tidak memengaruhi lingkup akses atasan maupun eskalasi; hanya informasi koordinasi/pengawasan."""

    class Kind(models.TextChoices):
        KOORDINASI = "KOORDINASI", "Koordinasi"
        PENGAWASAN = "PENGAWASAN", "Pengawasan"

    unit = models.ForeignKey(OrganizationUnit, on_delete=models.CASCADE, related_name="relations_out",
                             verbose_name="unit")
    target = models.ForeignKey(OrganizationUnit, on_delete=models.CASCADE, related_name="relations_in",
                               verbose_name="berhubungan dengan")
    kind = models.CharField("jenis hubungan", max_length=12, choices=Kind.choices, default=Kind.KOORDINASI)
    note = models.CharField("keterangan", max_length=255, blank=True)

    class Meta:
        verbose_name = "hubungan koordinasi/pengawasan"
        verbose_name_plural = "hubungan koordinasi/pengawasan"
        constraints = [
            models.UniqueConstraint(fields=["unit", "target", "kind"], name="uniq_org_relation"),
            models.CheckConstraint(condition=~models.Q(unit=models.F("target")), name="org_relation_not_self"),
        ]

    def __str__(self):
        return f"{self.unit.name} —{self.get_kind_display().lower()}→ {self.target.name}"


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
