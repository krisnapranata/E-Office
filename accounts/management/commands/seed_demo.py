"""Data sintetis untuk demo/testing. Jangan dijalankan di produksi."""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import OrganizationUnit, Role, User

UNITS = [
    ("DIR", "Direksi", None),
    ("YANMED", "Bidang Pelayanan Medis", "DIR"),
    ("IGD", "Instalasi Gawat Darurat", "YANMED"),
    ("FARM", "Instalasi Farmasi", "YANMED"),
    ("UMUM", "Bagian Umum", "DIR"),
]
USERS = [
    ("direktur", "Dr. Direktur Demo", Role.DIREKTUR, "DIR", None),
    ("sekretaris", "Sekretaris Demo", Role.SEKRETARIS, "DIR", "direktur"),
    ("wadir", "Wadir Yanmed Demo", Role.WADIR, "YANMED", "direktur"),
    ("ka_igd", "Kepala IGD Demo", Role.KEPALA_UNIT, "IGD", "wadir"),
    ("ka_farmasi", "Kepala Farmasi Demo", Role.KEPALA_UNIT, "FARM", "wadir"),
    ("staf_igd", "Staf IGD Demo", Role.STAF, "IGD", "ka_igd"),
    ("staf_farmasi", "Staf Farmasi Demo", Role.STAF, "FARM", "ka_farmasi"),
    ("arsip", "Petugas Arsip Demo", Role.ARSIP, "UMUM", "direktur"),
    ("auditor", "Auditor Demo", Role.AUDITOR, "DIR", None),
]


class Command(BaseCommand):
    help = "Membuat unit dan akun demo (data sintetis)."

    def add_arguments(self, parser):
        parser.add_argument("--password", required=True, help="Password untuk semua akun demo.")

    @transaction.atomic
    def handle(self, *args, password, **options):
        if len(password) < 8:
            raise CommandError("Password minimal 8 karakter.")
        units = {}
        for code, name, parent in UNITS:
            units[code], _ = OrganizationUnit.objects.update_or_create(
                code=code, defaults={"name": name, "parent": units.get(parent)})
        users = {}
        for username, name, role, unit, sup in USERS:
            first, _, last = name.partition(" ")
            u, _ = User.objects.update_or_create(
                username=username,
                defaults={"first_name": first, "last_name": last, "role": role,
                          "unit": units[unit], "supervisor": users.get(sup)})
            u.set_password(password)
            u.save()
            users[username] = u
        for code, head in [("DIR", "direktur"), ("YANMED", "wadir"), ("IGD", "ka_igd"),
                           ("FARM", "ka_farmasi")]:
            OrganizationUnit.objects.filter(code=code).update(head=users[head])
        self.stdout.write(self.style.SUCCESS(f"{len(users)} akun demo siap: "
                                             + ", ".join(users)))
