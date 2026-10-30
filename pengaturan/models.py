from django.conf import settings
from django.db import models


class PengaturanAplikasi(models.Model):
    """Pengaturan tunggal (pk=1). Disimpan di database agar bertahan saat image dibangun ulang/diperbarui."""

    class Mode(models.TextChoices):
        DEMO = "DEMO", "Mode demo"
        PRODUKSI = "PRODUKSI", "Mode produksi"

    mode = models.CharField("mode aplikasi", max_length=10, choices=Mode.choices, default=Mode.DEMO)
    direset_pada = models.DateTimeField("data demo direset pada", null=True, blank=True)
    direset_oleh = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name="+", verbose_name="direset oleh")
    # Aktif: Wakil Direktur & Kepala Unit hanya dapat menugaskan/mendisposisikan/menginstruksikan orang di unit sendiri
    # dan sub-unitnya (lihat pengaturan/aturan.py). Direktur tidak dibatasi. Bawaan nonaktif = perilaku lama.
    tugas_hanya_ke_bawah = models.BooleanField(
        "tugas hanya ke bawahan", default=False,
        help_text="Bila aktif, Wakil Direktur dan Kepala Unit hanya dapat memberi tugas, disposisi, dan instruksi "
                  "kepada pegawai di unit sendiri dan sub-unitnya.")
    diubah_pada = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "pengaturan aplikasi"
        verbose_name_plural = "pengaturan aplikasi"

    def __str__(self):
        return self.get_mode_display()

    @classmethod
    def ambil(cls):
        awal = getattr(settings, "EOFFICE_MODE_AWAL", cls.Mode.DEMO)
        obj, _ = cls.objects.get_or_create(pk=1, defaults={"mode": awal})
        return obj

    @property
    def is_demo(self):
        return self.mode == self.Mode.DEMO
