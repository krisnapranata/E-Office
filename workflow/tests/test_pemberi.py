"""'Siapa yang memberi tugas' (Task.pemberi / asal_singkat) dari keempat sumber, dan tampil di layar PIC."""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from testutils import factories as f
from workflow.models import Task


class PemberiTugasTests(TestCase):
    def setUp(self):
        self.w = f.World()

    def test_penugasan_langsung(self):
        t = f.direct_task(self.w.ka_igd, self.w.staf_igd, source_note="Bahan rapat evaluasi")
        self.assertEqual(t.pemberi, self.w.ka_igd)
        self.assertEqual(t.asal_singkat, "Penugasan langsung: Bahan rapat evaluasi")

    def test_instruksi_atas_nama_direktur(self):
        from instructions import services
        from instructions.models import InstructionTarget

        ins = services.create_instruction(self.w.sekretaris, on_behalf_of=self.w.direktur, title="Evaluasi IGD",
                                          description="x", instruction_date=f.today(),
                                          due_date=f.today() + timedelta(days=7))
        InstructionTarget.objects.create(instruction=ins, unit=self.w.igd, pic=self.w.ka_igd)
        services.issue(ins, self.w.direktur)
        t = ins.tasks.get()
        self.assertEqual(t.pemberi, self.w.direktur)                # bukan sekretaris yang mengetik
        self.assertEqual(t.asal_singkat, f"Instruksi {ins.code}: Evaluasi IGD")

    def test_disposisi(self):
        from letters import services

        surat = services.register_incoming(self.w.sekretaris, letter_number="1", letter_date=f.today(),
                                           received_date=f.today(), sender="Dinkes", subject="Permintaan data")
        d = services.create_disposition(self.w.direktur, surat, to_user=self.w.wadir, to_unit=self.w.yanmed,
                                        directive="Siapkan", due_date=f.today() + timedelta(days=5))
        t = Task.objects.get(disposition=d)
        self.assertEqual(t.pemberi, self.w.direktur)
        self.assertEqual(t.asal_singkat, "Disposisi surat: Permintaan data")

    def test_keputusan_rapat_dari_pimpinan_rapat(self):
        from agenda.services import create_event
        from notulen import services

        ev = create_event(self.w.direktur, participants=[self.w.ka_igd], title="Rapat mutu", kind="RAPAT",
                          start=timezone.now())
        m = services.create_minutes(self.w.sekretaris, ev, discussion="Bahas")
        k = services.add_decision(m, self.w.sekretaris, text="Perbaiki triase", requires_action=True,
                                  due_date=f.today() + timedelta(days=7))
        services.add_assignee(k, self.w.sekretaris, self.w.igd, self.w.ka_igd)
        services.submit(m, self.w.sekretaris)
        services.approve(m, self.w.direktur)
        t = Task.objects.get(decision=k)
        self.assertEqual(t.pemberi, ev.organizer)
        self.assertEqual(t.asal_singkat, "Keputusan rapat: Rapat mutu")

    def test_pic_melihat_pemberi_di_beranda_detail_dan_daftar(self):
        self.w.ka_igd.position = "Kepala Instalasi Gawat Darurat"
        self.w.ka_igd.save()
        t = f.direct_task(self.w.ka_igd, self.w.staf_igd, title="Rekap kunjungan")
        self.client.force_login(self.w.staf_igd)
        nama = str(self.w.ka_igd)
        beranda = self.client.get("/")
        self.assertIn(f"Dari {nama} (Kepala Instalasi Gawat Darurat)", beranda.context["kabar"][0]["ket"])
        html = self.client.get(reverse("workflow:detail", args=[t.pk])).content.decode()
        self.assertIn("Diberikan oleh", html)
        self.assertIn("Kepala Instalasi Gawat Darurat", html)
        self.assertIn(f"dari {nama}", self.client.get(reverse("workflow:list")).content.decode())

    def test_daftar_tugas_tanpa_query_per_baris(self):
        self.client.force_login(self.w.direktur)
        f.direct_task(self.w.ka_igd, self.w.staf_igd)
        self.client.get(reverse("workflow:list"))                  # pemanasan (cache sesi/ContentType)
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as satu:
            self.client.get(reverse("workflow:list"))
        for _ in range(4):
            f.direct_task(self.w.ka_farmasi, self.w.staf_farmasi)
        with CaptureQueriesContext(connection) as lima:
            self.client.get(reverse("workflow:list"))
        self.assertEqual(len(lima), len(satu), "jumlah query bertambah per baris (N+1)")
