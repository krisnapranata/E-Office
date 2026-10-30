"""Tampilan sederhana: Beranda 'Perlu Anda kerjakan', menu per peran, langkah & petunjuk di detail tugas."""
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

    def test_hasil_menunggu_diperiksa_muncul_untuk_pemeriksa(self):
        Task.objects.filter(pk=self.t.pk).update(status=TaskStatus.MENUNGGU_VERIFIKASI)
        judul = [x["judul"] for x in self.kabar(self.t.verifier)]
        self.assertIn("Hasil kerja menunggu Anda periksa", judul)
        self.assertEqual(self.kabar(self.w.staf_igd), [])          # PIC tinggal menunggu

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
