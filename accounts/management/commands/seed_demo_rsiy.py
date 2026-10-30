"""Pegawai CONTOH (fiktif, login demo_*) per unit Master Organisasi RSI Yatofa + isian contoh semua alur.

    manage.py seed_demo_rsiy --password '<sandi>'          # akun + isian alur (aman diulang)
    manage.py seed_demo_rsiy --password '<sandi>' --tanpa-alur
    manage.py seed_demo_rsiy --nonaktifkan                  # nonaktifkan semua akun demo_ (data tetap ada)
Jangan dijalankan di produksi.
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from accounts import demo_rsiy as demo


class Command(BaseCommand):
    help = "Membuat pegawai contoh RSI Yatofa (login demo_*) dan isian contoh semua alur E-Office."

    def add_arguments(self, parser):
        parser.add_argument("--password", help="Kata sandi untuk semua akun demo.")
        parser.add_argument("--tanpa-alur", action="store_true", help="Hanya akun, tanpa isian alur.")
        parser.add_argument("--nonaktifkan", action="store_true", help="Nonaktifkan semua akun demo_.")

    def handle(self, *args, password=None, tanpa_alur=False, nonaktifkan=False, **options):
        if not settings.DEBUG and not getattr(settings, "EOFFICE_IZINKAN_DEMO", False):
            raise CommandError("Ditolak: DEBUG=False (produksi). Data demo hanya untuk lingkungan dev/uji.")
        if nonaktifkan:
            self.stdout.write(self.style.SUCCESS(f"{demo.nonaktifkan_demo()} akun demo dinonaktifkan."))
            return
        if not password:
            raise CommandError("--password wajib diisi.")
        try:
            dibuat, diperbarui = demo.buat_pegawai(password)
        except ValidationError as e:
            raise CommandError("Kata sandi ditolak: " + " ".join(e.messages))
        self.stdout.write(self.style.SUCCESS(f"Pegawai demo: {dibuat} dibuat, {diperbarui} diperbarui."))
        if tanpa_alur:
            return
        hasil = demo.isi_alur()
        if hasil is None:
            self.stdout.write("Isian alur sudah ada sebelumnya — dilewati (tidak digandakan).")
        else:
            self.stdout.write(self.style.SUCCESS("Isian alur: " + ", ".join(f"{v} {k}" for k, v in hasil.items())))
