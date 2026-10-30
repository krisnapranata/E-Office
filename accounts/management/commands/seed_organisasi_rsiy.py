"""Isi Master Organisasi RSI Yatofa (aman dijalankan berulang; tidak menghapus/menggandakan data)."""
from django.core.management.base import BaseCommand

from accounts.organisasi import RSIY, seed_rsiy


class Command(BaseCommand):
    help = "Mengisi unit & hubungan koordinasi/pengawasan RSI Yatofa (idempotent, berdasarkan kode unit)."

    def add_arguments(self, parser):
        parser.add_argument("--paksa", action="store_true",
                            help="Kembalikan nama/jenis/induk/urutan unit RSIY-* yang sudah diubah ke versi bagan.")

    def handle(self, *args, paksa=False, **options):
        dibuat, diperbarui, relasi = seed_rsiy(paksa=paksa)
        self.stdout.write(self.style.SUCCESS(
            f"Master Organisasi RSI Yatofa: {len(RSIY)} unit di bagan · {dibuat} dibuat · {diperbarui} diperbarui · "
            f"{relasi} hubungan koordinasi/pengawasan baru."))
