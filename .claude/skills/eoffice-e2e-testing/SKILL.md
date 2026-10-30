---
name: eoffice-e2e-testing
description: Strategi pengujian E-Office — unit, integration (HTTP test client), dan E2E browser untuk 10 skenario PRD 18.4 C, dengan data sintetis dan waktu terkendali. Pakai saat menulis/menjalankan test, menambah skenario E2E, atau memverifikasi tampilan.
---

# Pengujian E-Office

## Lapisan & lokasi
| Lapisan | Lokasi | Alat |
|---|---|---|
| Unit (aturan bisnis) | `workflow/tests/test_services.py`, `notifications/tests/test_reminders.py`, `instructions/tests/`, `letters/tests/` | Django TestCase |
| Integration (view+DB+izin) | `dashboard/tests/test_integration.py` | `self.client` |
| E2E browser | belum ada — target `e2e/` | Playwright (rekomendasi PRD) |

Jalankan: `DJANGO_SETTINGS_MODULE=config.settings.test .venv/bin/python manage.py test --noinput [app]`.
DB test = `test_<DB_NAME>` di MariaDB (terpisah dari dev/prod). Jangan pernah mengarahkan test ke DB produksi.

## Data & waktu
- Data sintetis: `testutils/factories.py` (`World()` = DIR > YANMED > IGD, FARM; akun direktur, sekretaris, wadir, ka_igd, staf_igd, ka_farmasi,
  staf_farmasi, auditor). `f.direct_task(...)`, `f.dummy_file(...)`. Tidak boleh data pasien/pribadi nyata.
- Waktu: berikan `today=` ke `run_reminders` / `due_soon` / `overdue`, atau `send_reminders --date`. Jangan `sleep` menunggu tanggal.
- Celery: settings test `CELERY_TASK_ALWAYS_EAGER=True`; tetap ada satu test yang memanggil `run_daily_reminders.delay()`.

## 10 skenario E2E wajib (PRD 18.4 C) — status
1 Instruksi→penutupan (HTTP ✓) · 2 Surat & disposisi (HTTP ✓) · 3 Keputusan rapat (Tahap 2) · 4 Reminder H-2 (unit ✓) ·
5 Terlambat & eskalasi (unit ✓) · 6 Perlu perbaikan (unit ✓) · 7 Permission/kerahasiaan (HTTP ✓) · 8 Audit trail (unit ✓) ·
9 Filter dashboard (HTTP ✓) · 10 Kegagalan notifikasi (unit ✓). Semuanya masih perlu versi browser.

## Menambah E2E Playwright
1. `pip install pytest-playwright` di venv, patok versi di `requirements-dev.txt`, `playwright install chromium`.
2. Server uji: `StaticLiveServerTestCase` (DB test terisolasi) atau server terpisah dengan `seed_demo --password ...` di DB uji.
3. Login lewat form `#username` `#password` `#leTombol`; navigasi via menu sidebar (`.sidebar-link`), aksi lewat tombol berlabel.
4. Assert pada teks dari sistem (status, angka), bukan teks yang Anda ketik sendiri.

## Verifikasi visual (agent)
Untuk perubahan UI: jalankan `runserver 127.0.0.1:8011`, ambil screenshot dengan skill `browser-automation` (login → halaman terkait,
viewport 1440×900 dan 390×844), lihat gambarnya, laporkan yang terlihat. Periksa console error = 0 dan request gagal = 0.

## Laporan
Sebutkan perintah, jumlah test, hasil apa adanya; test yang tidak dijalankan disebut beserta alasannya.
