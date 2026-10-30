"""Grafik Laporan: angka grafik = angka tabel, sumbu bilangan bulat, SVG tidak rusak oleh format angka id-ID."""
import re
from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from laporan import grafik
from testutils import factories as f
from workflow import services as alur
from workflow.models import Task


class GrafikTests(TestCase):
    def test_sumbu_bilangan_bulat(self):
        for n in (0, 1, 5, 7, 23, 130):
            atas, garis = grafik._maks_rapi(n)
            self.assertGreaterEqual(atas, n)
            self.assertTrue(all(isinstance(g, int) for g in garis))
            self.assertLessEqual(len(garis), 6)

    def test_batang_unit_sama_dengan_tabel(self):
        baris = [{"kode": "IGD", "nama": "IGD", "total": 5, "selesai": 2, "selesai_terlambat": 1, "terbuka": 3,
                  "terlambat_terbuka": 1, "dibatalkan": 0},
                 {"kode": "GIZI", "nama": "Gizi", "total": 1, "selesai": 0, "selesai_terlambat": 0, "terbuka": 0,
                  "terlambat_terbuka": 0, "dibatalkan": 1}]
        g = grafik.per_unit(baris)
        self.assertEqual([r["kode"] for r in g["rows"]], ["IGD"])            # unit yang semua tugasnya batal tidak digambar
        self.assertEqual(g["rows"][0]["total"], 5)
        self.assertEqual([s["judul"] for s in g["rows"][0]["seg"]],
                         ["IGD — Selesai tepat waktu: 1", "IGD — Masih berjalan: 2", "IGD — Selesai terlambat: 1",
                          "IGD — Terlambat, belum selesai: 1"])

    def test_tren_label_tidak_bertumpuk_dan_bulan_indonesia(self):
        m = [{"mulai": date(2026, 10, 5) + timedelta(days=7 * i), "dibuat": 3, "selesai": 3} for i in range(3)]
        g = grafik.tren(m)
        self.assertGreaterEqual(abs(g["seri"][0]["label_y"] - g["seri"][1]["label_y"]), 14)
        self.assertEqual(g["sumbu_x"][0]["label"], "05 Okt")
        self.assertIsNone(grafik.tren(m[:1]))

    def test_halaman_laporan_memuat_svg_valid(self):
        w = f.World()
        t = f.direct_task(w.direktur, w.staf_igd, due=f.today() - timedelta(days=1))
        f.direct_task(w.direktur, w.staf_igd)
        alur.accept_task(t, w.staf_igd)
        self.client.force_login(w.direktur)
        dari = (f.today() - timedelta(days=20)).isoformat()
        r = self.client.get(reverse("laporan:index") + f"?dari={dari}&sampai={f.today().isoformat()}")
        html = r.content.decode()
        self.assertIn("Kondisi pekerjaan per unit", html)
        self.assertIn("Tugas baru vs tugas selesai per minggu", html)
        self.assertFalse(re.search(r'<(rect|circle|line|text)[^>]* (x|y|width|cx|cy|x1|y1)="[0-9]+,[0-9]', html),
                         "koordinat SVG memakai koma desimal")
        status = {b["label"]: b["n"] for b in r.context["rep"]["grafik"]["status"]}
        self.assertEqual(status, {"Menunggu penerimaan": 1, "Belum dimulai": 1})
        self.assertEqual(Task.objects.count(), 2)
