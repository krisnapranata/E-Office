from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from laporan.services import build, xlsx
from testutils import factories as f
from workflow import services as alur


class LaporanTests(TestCase):
    def test_metrics(self):
        w, today = f.World(), timezone.localdate()

        def buat(due, verif=True):
            return alur.create_task(created_by=w.ka_igd, source_type="LANGSUNG", source_note="x", title="t",
                                    unit=w.igd, pic=w.staf_igd, due_date=today + timedelta(days=due),
                                    requires_verification=verif, requires_evidence=False)

        a = buat(3)
        alur.accept_task(a, w.staf_igd)
        alur.report_progress(a, w.staf_igd, progress=100, status="BERJALAN")
        alur.submit_result(a, w.staf_igd)
        alur.verify(a, w.ka_igd, approved=True)
        b = buat(3, verif=False)
        alur.accept_task(b, w.staf_igd)
        alur.report_progress(b, w.staf_igd, progress=100, status="BERJALAN")
        alur.submit_result(b, w.staf_igd)
        buat(-1)
        c = buat(5)
        alur.cancel(c, w.ka_igd, "x")
        rk = build(w.direktur, dari=today, sampai=today)["ringkas"]
        self.assertEqual(rk["total"], 4)
        self.assertEqual((rk["selesai"], rk["selesai_terverifikasi"], rk["selesai_tanpa_verifikasi"]), (2, 1, 1))
        self.assertEqual((rk["terlambat_terbuka"], rk["dibatalkan"], rk["pct_tepat_waktu"]), (1, 1, 100))
        self.assertEqual(rk["pct_selesai"], 67)
        self.assertEqual(build(w.staf_farmasi, dari=today, sampai=today)["ringkas"]["total"], 0)
        self.assertTrue(xlsx(build(w.direktur, dari=today, sampai=today)).startswith(b"PK"))
