from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from accounts.files import protected_upload_to, validate_upload
from accounts.permissions import Classification


def arsip_upload_to(instance, filename):
    return protected_upload_to("arsip")(instance, filename)


class ArchiveDocument(models.Model):
    """Satu dokumen arsip + metadata. Dokumen dari modul lain MERUJUK objek asalnya (source) dan berkasnya."""

    class DocType(models.TextChoices):
        SURAT_MASUK = "SURAT_MASUK", "Surat masuk"
        SURAT_KELUAR = "SURAT_KELUAR", "Surat keluar"
        INSTRUKSI = "INSTRUKSI", "Instruksi"
        AGENDA = "AGENDA", "Bahan agenda/rapat"
        NOTULEN = "NOTULEN", "Notulen"
        BUKTI = "BUKTI", "Bukti pelaksanaan"
        LAPORAN = "LAPORAN", "Laporan"
        LAINNYA = "LAINNYA", "Lainnya"

    class Status(models.TextChoices):
        AKTIF = "AKTIF", "Aktif"
        DIUSULKAN = "DIUSULKAN", "Diusulkan musnah"
        DIMUSNAHKAN = "DIMUSNAHKAN", "Dimusnahkan"

    doc_type = models.CharField("jenis", max_length=15, choices=DocType.choices, db_index=True)
    number = models.CharField("nomor", max_length=100, blank=True, db_index=True)
    doc_date = models.DateField("tanggal dokumen", db_index=True)
    title = models.CharField("judul", max_length=255)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+",
                              verbose_name="pemilik")
    unit = models.ForeignKey("accounts.OrganizationUnit", null=True, blank=True, on_delete=models.PROTECT,
                             related_name="+", verbose_name="unit")
    classification = models.CharField("klasifikasi", max_length=10, choices=Classification.CHOICES,
                                      default=Classification.BIASA)
    keywords = models.CharField("kata kunci", max_length=255, blank=True)
    source_type = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    source_id = models.PositiveBigIntegerField(null=True, blank=True)
    source = GenericForeignKey("source_type", "source_id")
    retention_until = models.DateField("retensi sampai", db_index=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.AKTIF, db_index=True)
    disposal_note = models.TextField("catatan/berita acara pemusnahan", blank=True)
    disposal_proposed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                             on_delete=models.PROTECT, related_name="+")
    disposal_approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                             on_delete=models.PROTECT, related_name="+")
    disposed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-doc_date", "-id"]
        verbose_name = "dokumen arsip"
        verbose_name_plural = "dokumen arsip"
        indexes = [models.Index(fields=["source_type", "source_id"])]
        constraints = [models.UniqueConstraint(fields=["source_type", "source_id", "doc_type"],
                                               name="uniq_archive_per_source")]

    def __str__(self):
        return f"{self.get_doc_type_display()} {self.number or ''} {self.title}".strip()

    @property
    def latest(self):
        return self.versions.order_by("-version").first()


class ArchiveVersion(models.Model):
    """Versi berkas. Revisi = versi baru; versi lama tetap tersimpan."""

    document = models.ForeignKey(ArchiveDocument, on_delete=models.PROTECT, related_name="versions")
    version = models.PositiveSmallIntegerField()
    file = models.FileField(upload_to=arsip_upload_to, max_length=255, validators=[validate_upload])
    original_name = models.CharField(max_length=255)
    note = models.CharField("catatan versi", max_length=255, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version"]
        constraints = [models.UniqueConstraint(fields=["document", "version"], name="uniq_archive_version")]

    def __str__(self):
        return f"v{self.version} {self.original_name}"
