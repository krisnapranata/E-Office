"""Dijalankan entrypoint container setelah migrate: muat data demo hanya bila Mode Demo dan belum pernah dimuat.
Setelah reset (Mode Produksi), build/update berikutnya tidak memuat data demo lagi."""
from django.core.management.base import BaseCommand

from pengaturan.services import muat_otomatis


class Command(BaseCommand):
    help = "Muat data demo otomatis sesuai Pengaturan Aplikasi (aman diulang)."

    def handle(self, *args, **options):
        self.stdout.write(muat_otomatis())
