"""Aturan "tugas hanya ke bawahan": nonaktif = perilaku lama; aktif = Wadir/Kepala Unit hanya ke unit & sub-unitnya."""
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts.models import Role
from audit.models import AuditLog
from pengaturan.models import PengaturanAplikasi
from testutils import factories as f
from workflow import services as alur
from workflow.forms import DirectTaskForm
from workflow.models import TaskSource


def nyalakan(aktif=True):
    p = PengaturanAplikasi.ambil()
    p.tugas_hanya_ke_bawah = aktif
    p.save()


class AturanKeBawahTests(TestCase):
    def setUp(self):
        self.w = f.World()

    def tugas(self, pemberi, pic, **kw):
        return f.direct_task(pemberi, pic, **kw)

    def test_nonaktif_bawaan_perilaku_lama(self):
        self.assertFalse(PengaturanAplikasi.ambil().tugas_hanya_ke_bawah)
        self.tugas(self.w.ka_igd, self.w.staf_farmasi)                       # lintas unit tetap boleh
        self.assertIn(self.w.staf_farmasi, DirectTaskForm(pemberi=self.w.ka_igd).fields["pic"].queryset)

    def test_aktif_kepala_unit_hanya_ke_unitnya(self):
        nyalakan()
        with self.assertRaises(ValidationError) as e:
            self.tugas(self.w.ka_igd, self.w.staf_farmasi)
        self.assertIn("pic", e.exception.message_dict)
        self.tugas(self.w.ka_igd, self.w.staf_igd)                           # bawahan sendiri: boleh
        pilihan = DirectTaskForm(pemberi=self.w.ka_igd).fields["pic"].queryset
        self.assertIn(self.w.staf_igd, pilihan)
        self.assertNotIn(self.w.staf_farmasi, pilihan)
        self.assertNotIn(self.w.direktur, pilihan)

    def test_aktif_wadir_ke_sub_unit_boleh(self):
        nyalakan()
        self.tugas(self.w.wadir, self.w.staf_igd)                            # IGD di bawah Yanmed
        with self.assertRaises(ValidationError):
            self.tugas(self.w.wadir, self.w.staf_farmasi)

    def test_direktur_dan_kolaborator_tidak_dibatasi(self):
        nyalakan()
        self.tugas(self.w.direktur, self.w.staf_farmasi)
        t = alur.create_task(created_by=self.w.ka_igd, source_type=TaskSource.LANGSUNG, source_note="x",
                             title="Lintas unit", unit=self.w.igd, pic=self.w.staf_igd,
                             due_date=f.today() + timedelta(days=3), collaborators=[self.w.staf_farmasi])
        self.assertEqual(list(t.collaborators.all()), [self.w.staf_farmasi])
        self.assertIn(self.w.staf_farmasi, DirectTaskForm(pemberi=self.w.ka_igd).fields["collaborators"].queryset)

    def test_aktif_ubah_pic_ke_luar_unit_ditolak(self):
        t = self.tugas(self.w.ka_igd, self.w.staf_igd)
        nyalakan()
        with self.assertRaises(ValidationError):
            alur.reassign(t, self.w.ka_igd, pic=self.w.staf_farmasi, reason="rotasi")
        alur.reassign(t, self.w.direktur, pic=self.w.staf_farmasi, reason="rotasi")   # Direktur boleh

    def test_aktif_disposisi_dibatasi(self):
        from letters import services as surat

        s = surat.register_incoming(self.w.sekretaris, letter_number="1", letter_date=f.today(),
                                    received_date=f.today(), sender="Dinkes", subject="Data")
        nyalakan()
        induk = surat.create_disposition(self.w.direktur, s, to_user=self.w.wadir, to_unit=self.w.yanmed,
                                         directive="Siapkan", due_date=f.today() + timedelta(days=5))
        with self.assertRaises(ValidationError) as e:
            surat.create_disposition(self.w.wadir, s, parent=induk, to_user=self.w.ka_farmasi, to_unit=self.w.farmasi,
                                     directive="x", due_date=f.today() + timedelta(days=3))
        self.assertIn("to_user", e.exception.message_dict)
        surat.create_disposition(self.w.wadir, s, parent=induk, to_user=self.w.ka_igd, to_unit=self.w.igd,
                                 directive="Teruskan", due_date=f.today() + timedelta(days=3))

    def test_aktif_instruksi_dihitung_dari_pemberi_atas_nama(self):
        from instructions import services as ins
        from instructions.models import InstructionTarget

        nyalakan()

        def instruksi(atas_nama):
            i = ins.create_instruction(self.w.sekretaris, on_behalf_of=atas_nama, title="Evaluasi", description="x",
                                       instruction_date=f.today(), due_date=f.today() + timedelta(days=7))
            InstructionTarget.objects.create(instruction=i, unit=self.w.farmasi, pic=self.w.ka_farmasi)
            return i
        with self.assertRaises(ValidationError):
            ins.issue(instruksi(self.w.wadir), self.w.sekretaris)            # Wadir Yanmed -> Farmasi: ditolak
        ins.issue(instruksi(self.w.direktur), self.w.sekretaris)              # atas nama Direktur: boleh

    def test_halaman_pengaturan_hanya_admin_dan_tercatat(self):
        admin = f.user(Role.ADMIN)
        self.client.force_login(self.w.ka_igd)
        self.assertEqual(self.client.post(reverse("pengaturan:aturan"), {"aktif": "1"}).status_code, 403)
        self.assertFalse(PengaturanAplikasi.ambil().tugas_hanya_ke_bawah)
        self.client.force_login(admin)
        r = self.client.post(reverse("pengaturan:aturan"), {"aktif": "1"}, follow=True)
        self.assertContains(r, "AKTIF")
        self.assertTrue(PengaturanAplikasi.ambil().tugas_hanya_ke_bawah)
        self.assertTrue(AuditLog.objects.filter(action="app.aturan.ke_bawah", user=admin).exists())
        self.client.post(reverse("pengaturan:aturan"), {"aktif": "0"})
        self.assertFalse(PengaturanAplikasi.ambil().tugas_hanya_ke_bawah)

    def test_panduan_menyebut_status_aturan(self):
        self.client.force_login(self.w.staf_igd)
        self.assertIn("tidak aktif", str(self.client.get(reverse("panduan:index")).context["alur_tugas"]["catatan"]))
        nyalakan()
        r = self.client.get(reverse("panduan:index"))
        self.assertIn(": aktif.", str(r.context["alur_tugas"]["catatan"]))
        baris = dict(r.context["alur_tugas"]["matriks"]["baris"])
        self.assertEqual(baris["Memberi penugasan langsung"][2], ("syarat", "hanya ke unit & sub-unitnya"))
