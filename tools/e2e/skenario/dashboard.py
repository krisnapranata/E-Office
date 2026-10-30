"""Executive Dashboard: skenario E2E PRD 18.4 C no. 9 — angka ringkasan = jumlah di daftar detail, per peran."""
from datetime import timedelta

from django.utils import timezone

from workflow import services as alur

from . import skenario
from ._bantu import JUDUL_QA, jumlah_daftar, kartu_dashboard, url


@skenario("dashboard", "Setiap angka kartu status = jumlah daftar terfilter (semua peran)",
          menu=["dashboard:home", "workflow:list"])
def _(u):
    w, hari_ini = u.w, timezone.localdate()
    for i, (n, pic) in enumerate([(-2, w.staf_igd), (1, w.staf_igd), (5, w.staf_farmasi), (-1, w.staf_farmasi)]):
        alur.create_task(created_by=w.direktur, source_type="LANGSUNG", source_note="QA",
                         title=f"{JUDUL_QA} Dashboard {i}", unit=pic.unit, pic=pic,
                         due_date=hari_ini + timedelta(days=n))
    for peran in ("direktur", "wadir", "ka_igd", "staf_igd", "ka_farmasi", "auditor"):
        u.sebagai(peran)
        kartu = kartu_dashboard(u.teks(u.get("/")))
        u.harap(len(kartu) == 8, f"{peran}: {len(kartu)} kartu status (harap 8)")
        for label, angka, qs in kartu:
            if label == "Belum dimulai":       # kartu gabungan 2 status; tautan menuju salah satunya
                continue
            n = jumlah_daftar(u.teks(u.get(url("workflow:list") + "?" + qs)))
            u.harap(n == angka, f"{peran}: kartu '{label}' = {angka}, daftar ?{qs} = {n}")
    u.sebagai("ka_igd")       # lingkup unit: hanya IGD
    terlambat = dict((lbl, n) for lbl, n, _ in kartu_dashboard(u.teks(u.get("/"))))["Terlambat"]
    u.harap(terlambat == 1, f"ka_igd melihat {terlambat} tugas terlambat (harap 1, hanya unit IGD)")
