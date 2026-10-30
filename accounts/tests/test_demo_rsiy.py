from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from accounts import demo_rsiy as demo
from accounts.models import OrganizationUnit, Role, User
from agenda.models import AgendaEvent
from arsip.models import ArchiveDocument
from audit.models import AuditLog
from instructions.models import Instruction
from letters.models import Disposition, IncomingLetter
from notifications.models import Notification
from notulen.models import MeetingMinutes
from workflow.models import Task, TaskStatus as S

SANDI = "Demo-RSIY-2026!"


@override_settings(DEBUG=True)
class SeedDemoRsiyTests(TestCase):
    def jalankan(self, *args):
        call_command("seed_demo_rsiy", *args, stdout=StringIO())

    def test_pegawai_mengikuti_struktur(self):
        self.jalankan("--password", SANDI, "--tanpa-alur")
        u = lambda n: User.objects.get(username="demo_" + n)  # noqa: E731
        self.assertEqual(User.objects.filter(username__startswith="demo_").count(), len(demo.PEGAWAI))
        self.assertEqual((u("ahmad.fauzi").role, u("ahmad.fauzi").unit.code), (Role.DIREKTUR, "RSIY-DIR"))
        self.assertEqual(u("budi.santoso").role, Role.WADIR)
        self.assertEqual(u("budi.santoso").supervisor, u("ahmad.fauzi"))
        self.assertEqual(u("fajar.nugroho").supervisor, u("eko.saputra"))
        self.assertEqual(u("fajar.nugroho").position, "Staf Instalasi Gawat Darurat")
        self.assertEqual(u("eko.saputra").position, "Kepala Instalasi Gawat Darurat")
        self.assertEqual(u("bayu.saputra").supervisor, u("sutrisno"))          # unit tanpa kepala -> induk
        self.assertEqual(OrganizationUnit.objects.get(code="RSIY-IGD").head, u("eko.saputra"))
        self.assertEqual(u("dimas.aditya").role, Role.ADMIN)
        self.assertTrue(u("dimas.aditya").check_password(SANDI))
        # setiap unit aktif berpengguna
        kosong = OrganizationUnit.objects.filter(code__startswith="RSIY-").exclude(members__username__startswith="demo_")
        self.assertFalse(kosong.exists(), list(kosong.values_list("code", flat=True)))

    def test_isian_alur_lengkap_dan_tidak_ganda(self):
        self.jalankan("--password", SANDI)
        status = set(Task.objects.values_list("status", flat=True))
        for s in (S.MENUNGGU_PENERIMAAN, S.BELUM_DIMULAI, S.BERJALAN, S.TERHAMBAT, S.MENUNGGU_VERIFIKASI,
                  S.PERLU_PERBAIKAN, S.SELESAI, S.DIBATALKAN):
            self.assertIn(s, status)
        self.assertEqual(IncomingLetter.objects.count(), 4)
        self.assertEqual(Disposition.objects.count(), 5)
        self.assertTrue(Instruction.objects.filter(status=Instruction.Status.DRAF).exists())
        self.assertEqual(set(MeetingMinutes.objects.values_list("status", flat=True)), {"DISETUJUI", "DIAJUKAN"})
        self.assertTrue(Task.objects.filter(source_type="KEPUTUSAN_RAPAT").exists())
        self.assertTrue(AgendaEvent.objects.filter(status=AgendaEvent.Status.DIBATALKAN).exists())
        self.assertTrue(ArchiveDocument.objects.filter(status=ArchiveDocument.Status.DIUSULKAN).exists())
        self.assertTrue(Notification.objects.filter(kind__icontains="escal").exists()
                        or Notification.objects.filter(title__icontains="eskalasi").exists())
        jumlah = (Task.objects.count(), AuditLog.objects.count())
        self.jalankan("--password", SANDI)                                     # ulang: tidak ganda
        self.assertEqual(Task.objects.count(), jumlah[0])

    def test_nonaktifkan(self):
        self.jalankan("--password", SANDI, "--tanpa-alur")
        self.jalankan("--nonaktifkan")
        self.assertFalse(User.objects.filter(username__startswith="demo_", is_active=True).exists())
        self.assertIsNone(OrganizationUnit.objects.get(code="RSIY-DIR").head)

    @override_settings(DEBUG=False)
    def test_ditolak_di_produksi(self):
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            self.jalankan("--password", SANDI)
