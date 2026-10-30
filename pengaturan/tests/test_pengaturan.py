from io import StringIO

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import OrganizationUnit, Role, User
from audit.models import AuditLog
from letters.models import Disposition, IncomingLetter
from pengaturan import services as svc
from pengaturan.models import PengaturanAplikasi
from testutils import factories as f
from workflow import services as wf
from workflow.models import Task, TaskEvidence

SANDI = "Demo-RSIY-2026!"


@override_settings(EOFFICE_DEMO_PASSWORD=SANDI)
class ModeDemoTests(TestCase):
    def setUp(self):
        self.admin = f.user(Role.ADMIN, username="admin_asli")
        # data ASLI yang tidak boleh ikut terhapus
        self.unit_asli = f.unit("ASLI")
        self.pic_asli = f.user(Role.STAF, unit=self.unit_asli, username="pegawai_asli")
        self.tugas_asli = wf.create_task(created_by=self.admin, title="Tugas asli", source_type="LANGSUNG",
                                         source_note="nyata", unit=self.unit_asli, pic=self.pic_asli)

    def otomatis(self):
        out = StringIO()
        call_command("demo_otomatis", stdout=out)
        return out.getvalue()

    def test_build_pertama_memuat_demo_sekali(self):
        self.assertIn("akun demo dibuat", self.otomatis())
        self.assertTrue(PengaturanAplikasi.ambil().is_demo)
        n = Task.objects.count()
        self.assertGreater(n, 15)
        self.assertIn("sudah ada", self.otomatis())                  # restart/update: tidak ganda
        self.assertEqual(Task.objects.count(), n)

    def test_reset_hapus_demo_saja_lalu_build_tidak_memuat_lagi(self):
        self.otomatis()
        bukti = TaskEvidence.objects.filter(uploaded_by__username__startswith="demo_").first()
        self.assertTrue(default_storage.exists(bukti.file.name))
        with self.captureOnCommitCallbacks(execute=True):
            jumlah = svc.reset_demo(self.admin, "reset data demo")
        self.assertEqual(jumlah["akun demo"], 69)
        self.assertFalse(User.objects.filter(username__startswith="demo_").exists())
        self.assertFalse(IncomingLetter.objects.exists())
        self.assertFalse(Disposition.objects.exists())                # termasuk disposisi berjenjang
        self.assertEqual(list(Task.objects.all()), [self.tugas_asli])  # data asli utuh
        self.assertTrue(User.objects.filter(username="pegawai_asli").exists())
        self.assertEqual(OrganizationUnit.objects.filter(code__startswith="RSIY-").count(), 50)
        self.assertFalse(default_storage.exists(bukti.file.name))     # berkas demo ikut dihapus
        p = PengaturanAplikasi.ambil()
        self.assertEqual((p.mode, p.direset_oleh), (PengaturanAplikasi.Mode.PRODUKSI, self.admin))
        self.assertTrue(AuditLog.objects.filter(action="app.demo.reset").exists())
        self.assertIn("Mode produksi", self.otomatis())               # update/build ulang: tidak dimuat
        self.assertFalse(User.objects.filter(username__startswith="demo_").exists())

    def test_aktifkan_demo_lagi_setelah_reset(self):
        self.otomatis()
        svc.reset_demo(self.admin, svc.FRASA_RESET)
        dibuat, alur = svc.muat_demo(self.admin)
        self.assertEqual(dibuat, 69)
        self.assertTrue(alur)
        self.assertTrue(PengaturanAplikasi.ambil().is_demo)

    def test_pengaman_reset(self):
        self.otomatis()
        with self.assertRaises(ValidationError):
            svc.reset_demo(self.admin, "reset")                      # frasa salah
        with self.assertRaises(ValidationError):
            svc.reset_demo(User.objects.get(username="demo_dimas.aditya"), svc.FRASA_RESET)   # akun demo
        with self.assertRaises(PermissionDenied):
            svc.reset_demo(self.pic_asli, svc.FRASA_RESET)
        # data asli yang merujuk akun demo -> reset dibatalkan seluruhnya, tidak ada yang terhapus
        wf.create_task(created_by=self.admin, title="Asli dengan PIC demo", source_type="LANGSUNG", source_note="x",
                       unit=self.unit_asli, pic=User.objects.get(username="demo_fajar.nugroho"))
        jumlah = (User.objects.count(), Task.objects.count(), IncomingLetter.objects.count())
        with self.assertRaisesMessage(ValidationError, "Reset dibatalkan"):
            svc.reset_demo(self.admin, svc.FRASA_RESET)
        self.assertEqual((User.objects.count(), Task.objects.count(), IncomingLetter.objects.count()), jumlah)
        self.assertTrue(PengaturanAplikasi.ambil().is_demo)

    @override_settings(EOFFICE_DEMO_PASSWORD="")
    def test_tanpa_sandi_demo_tidak_dimuat(self):
        self.assertIn("belum diisi", self.otomatis())
        self.assertFalse(User.objects.filter(username__startswith="demo_").exists())
        with self.assertRaises(ValidationError):
            svc.muat_demo(self.admin)

    def test_halaman(self):
        self.client.force_login(self.pic_asli)
        self.assertEqual(self.client.get(reverse("pengaturan:index")).status_code, 403)
        self.assertEqual(self.client.post(reverse("pengaturan:reset"), {"frasa": svc.FRASA_RESET}).status_code, 403)
        self.client.force_login(self.admin)
        r = self.client.post(reverse("pengaturan:demo"), follow=True)
        self.assertContains(r, "Mode Demo aktif")
        self.assertContains(r, "MODE DEMO")                           # penanda di bilah atas
        r = self.client.post(reverse("pengaturan:reset"), {"frasa": svc.FRASA_RESET}, follow=True)
        self.assertContains(r, "Mode Produksi aktif")
        self.assertNotContains(r, "MODE DEMO")
