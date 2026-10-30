"""Tampilan sederhana: Beranda 'Perlu Anda kerjakan', menu per peran, langkah & petunjuk di detail tugas."""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse

from testutils import factories as f
from workflow.models import Task, TaskStatus


class BerandaTests(TestCase):
    def setUp(self):
        self.w = f.World()
        self.t = f.direct_task(self.w.ka_igd, self.w.staf_igd, title="Cek troli emergensi")

    def kabar(self, user):
        self.client.force_login(user)
        return self.client.get(reverse("dashboard:home")).context["kabar"]

    def test_tugas_baru_muncul_untuk_pic_saja(self):
        k = self.kabar(self.w.staf_igd)
        self.assertEqual([(x["judul"], x["teks"], x["tombol"]) for x in k],
                         [("Tugas baru untuk Anda", "Cek troli emergensi", "Lihat & terima")])
        self.assertEqual(k[0]["url"], reverse("workflow:detail", args=[self.t.pk]))
        self.assertEqual(self.kabar(self.w.staf_farmasi), [])

    def ctx(self, user):
        self.client.force_login(user)
        return self.client.get(reverse("dashboard:home")).context

    def test_hasil_menunggu_diperiksa_masuk_keputusan_pemeriksa(self):
        Task.objects.filter(pk=self.t.pk).update(status=TaskStatus.MENUNGGU_VERIFIKASI)
        judul = [x["judul"] for x in self.ctx(self.t.verifier)["keputusan"]]
        self.assertIn("Hasil kerja menunggu Anda periksa", judul)
        self.assertEqual(self.kabar(self.w.staf_igd), [])          # PIC tinggal menunggu

    def test_permintaan_keputusan_pic_sampai_ke_pimpinan_lalu_hilang_setelah_arahan(self):
        from workflow import services as alur
        alur.accept_task(self.t, self.w.staf_igd)
        alur.report_progress(self.t, self.w.staf_igd, progress=30, status=TaskStatus.TERHAMBAT,
                             obstacle="Troli kurang 2", decision_needed="Boleh beli troli baru?")
        for pimpinan in (self.w.direktur, self.w.ka_igd):
            k = [x for x in self.ctx(pimpinan)["keputusan"] if x["tombol"] == "Beri arahan"]
            self.assertEqual([x["teks"] for x in k], ["Boleh beli troli baru?"], pimpinan)
        ctx = self.ctx(self.w.direktur)
        self.assertEqual([x["t"] for x in ctx["kejar_terhambat"]], [self.t])
        self.assertEqual(ctx["kejar_terhambat"][0]["hambatan"], "Troli kurang 2")
        self.assertEqual([x["teks"] for x in self.ctx(self.w.staf_farmasi)["kabar"]], [])     # bukan urusannya
        self.client.force_login(self.w.direktur)
        r = self.client.post(reverse("workflow:direction", args=[self.t.pk]), {"note": "Setuju, beli 2 unit."})
        self.assertEqual(r.status_code, 302)
        self.assertFalse([x for x in self.ctx(self.w.direktur)["keputusan"] if x["tombol"] == "Beri arahan"])
        self.assertTrue(self.t.updates.filter(note="Arahan pimpinan: Setuju, beli 2 unit.").exists())
        self.assertTrue(self.w.staf_igd.notifications.filter(kind="task.direction").exists())
        self.client.force_login(self.w.staf_farmasi)                                      # bukan pengelola
        self.assertEqual(self.client.post(reverse("workflow:direction", args=[self.t.pk]), {"note": "x"}).status_code, 404)

    def test_terlambat_bisa_dikejar_dari_beranda(self):
        Task.objects.filter(pk=self.t.pk).update(due_date=f.today() - timedelta(days=3))
        ctx = self.ctx(self.w.direktur)
        self.assertEqual([(x["t"].pk, x["hari"]) for x in ctx["kejar_terlambat"]], [(self.t.pk, 3)])
        r = self.client.post(reverse("workflow:request_update", args=[self.t.pk]), {"next": "/"})
        self.assertRedirects(r, "/", fetch_redirect_response=False)
        r = self.client.post(reverse("workflow:request_update", args=[self.t.pk]), {"next": "https://jahat.example/"})
        self.assertEqual(r["Location"], reverse("workflow:detail", args=[self.t.pk]))      # bukan open redirect

    def test_kartu_status_kepala_unit_menghitung_semua_tugas(self):
        """Regresi: queryset distinct() + ordering bawaan membuat setiap status terhitung 1."""
        from workflow import services as alur
        for i in range(3):
            t = f.direct_task(self.w.ka_igd, self.w.staf_igd, title=f"Jalan {i}")
            alur.accept_task(t, self.w.staf_igd)
            alur.report_progress(t, self.w.staf_igd, progress=10, status=TaskStatus.BERJALAN)
        kartu = {lbl: n for lbl, n, _, _ in self.ctx(self.w.ka_igd)["cards"]}
        self.assertEqual(kartu["Berjalan"], 3)

    def test_menu_per_peran(self):
        self.client.force_login(self.w.staf_igd)
        html = self.client.get(reverse("dashboard:home")).content.decode()
        for url in ("dashboard:home", "workflow:list", "instructions:list", "agenda:list", "panduan:index"):
            self.assertIn(f'href="{reverse(url)}"', html)
        for url in ("letters:incoming_list", "laporan:index", "organisasi:index", "pengguna:index"):
            self.assertNotIn(f'href="{reverse(url)}"', html)
        self.client.force_login(self.w.direktur)
        html = self.client.get(reverse("dashboard:home")).content.decode()
        for url in ("letters:incoming_list", "letters:disposition_list", "laporan:index", "organisasi:index"):
            self.assertIn(f'href="{reverse(url)}"', html)
        self.assertNotIn(f'href="{reverse("pengguna:index")}"', html)

    def test_detail_tugas_langkah_dan_petunjuk(self):
        self.client.force_login(self.w.staf_igd)
        r = self.client.get(reverse("workflow:detail", args=[self.t.pk]))
        self.assertEqual([k for _, k in r.context["langkah"]], ["selesai", "sekarang", "nanti", "nanti", "nanti"])
        self.assertIn("Terima tugas", r.context["petunjuk"])

    def test_tab_daftar_tugas(self):
        self.client.force_login(self.w.staf_igd)
        r = self.client.get(reverse("workflow:list") + "?status=MENUNGGU_PENERIMAAN")
        self.assertEqual([lbl for lbl, _, aktif in r.context["tab"] if aktif], ["Perlu diterima"])
        self.assertEqual(r.context["page"].paginator.count, 1)


class PratinjauBerkasTests(TestCase):
    """Berkas PDF/gambar bisa DILIHAT di browser (?lihat=1); Word/Excel tetap diunduh; akses & audit sama."""

    def setUp(self):
        from django.test import override_settings
        import tempfile
        self._media = override_settings(MEDIA_ROOT=tempfile.mkdtemp())
        self._media.enable()
        from workflow import services as alur
        self.w = f.World()
        self.t = f.direct_task(self.w.ka_igd, self.w.staf_igd)
        alur.accept_task(self.t, self.w.staf_igd)
        self.pdf = alur.add_evidence(self.t, self.w.staf_igd, f.dummy_file("bukti.pdf"))
        self.doc = alur.add_evidence(self.t, self.w.staf_igd, f.dummy_file("rekap.docx", b"PK\x03\x04"))

    def tearDown(self):
        self._media.disable()

    def get(self, ev, q=""):
        return self.client.get(reverse("workflow:evidence_download", args=[ev.pk]) + q)

    def test_pdf_tampil_di_browser(self):
        from audit.models import AuditLog
        self.client.force_login(self.w.ka_igd)
        r = self.get(self.pdf, "?lihat=1")
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertTrue(r["Content-Disposition"].startswith("inline"))
        self.assertEqual(r["X-Frame-Options"], "SAMEORIGIN")
        self.assertEqual(r["X-Content-Type-Options"], "nosniff")
        self.assertTrue(AuditLog.objects.filter(action="task.evidence.view").exists())
        r = self.get(self.pdf)                                        # tanpa ?lihat tetap unduhan
        self.assertTrue(r["Content-Disposition"].startswith("attachment"))

    def test_word_tetap_diunduh_dan_akses_tetap_dicek(self):
        self.client.force_login(self.w.ka_igd)
        self.assertTrue(self.get(self.doc, "?lihat=1")["Content-Disposition"].startswith("attachment"))
        self.client.force_login(self.w.staf_farmasi)
        self.assertEqual(self.get(self.pdf, "?lihat=1").status_code, 404)

    def test_tombol_lihat_hanya_untuk_pdf_gambar(self):
        self.client.force_login(self.w.ka_igd)
        html = self.client.get(reverse("workflow:detail", args=[self.t.pk])).content.decode()
        self.assertIn(reverse("workflow:evidence_download", args=[self.pdf.pk]) + "?lihat=1", html)
        self.assertNotIn(reverse("workflow:evidence_download", args=[self.doc.pk]) + "?lihat=1", html)
