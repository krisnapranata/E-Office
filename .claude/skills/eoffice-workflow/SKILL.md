---
name: eoffice-workflow
description: Aturan bisnis inti E-Office — disposisi, instruksi, mesin status tugas, bukti & verifikasi, reminder H-2/terlambat/eskalasi, isolasi antrean Celery, dan audit trail. Pakai saat mengubah alur kerja, status, reminder, atau job background.
---

# Workflow E-Office

## Mesin status tugas (`workflow/services.py::ALLOWED_TRANSITIONS`)
DRAF → MENUNGGU_PENERIMAAN → BELUM_DIMULAI → BERJALAN ⇄ TERHAMBAT → MENUNGGU_VERIFIKASI → SELESAI;
MENUNGGU_VERIFIKASI → PERLU_PERBAIKAN → BERJALAN/TERHAMBAT/MENUNGGU_VERIFIKASI; BERJALAN → SELESAI hanya bila verifikasi tidak wajib;
semua status terbuka → DIBATALKAN (alasan wajib). SELESAI/DIBATALKAN final.
Tabel yang sama ada di PRD Bab 8 — ubah keduanya bersamaan.

## Aturan (PRD Bab 8)
- *Terlambat* dan *H-2* = penanda terhitung (`TaskQuerySet.overdue/due_soon`, `Task.is_overdue`), **bukan** status.
- Progres 100% tidak menutup tugas. Penutupan: `submit_result` → `verify`.
- TERHAMBAT wajib uraian hambatan; pengembalian perbaikan & pembatalan wajib alasan; bukti wajib sebelum kirim bila `requires_evidence`.
- Ubah PIC/tenggat lewat `reassign` (alasan wajib, diaudit, PIC baru dinotifikasi).
- Instruksi: hanya draf yang bisa diubah; `issue` membuat satu Task per `InstructionTarget`; batal instruksi membatalkan tugas terbukanya.
- Disposisi `requires_action` wajib tenggat dan membuat satu Task; status disposisi mengikuti tugas (`sync_disposition_status`).
  Penerusan hanya oleh penerima disposisi asal (`parent`).
- Setiap perubahan status → `audit.log(... "task.status" ...)` otomatis di `_set_status`.

## Reminder (`notifications/services.py::run_reminders(today)`)
- H-n dari `settings.EOFFICE["REMINDER_DAYS_BEFORE"]` (default `[2]`), terlambat sekali per tenggat, eskalasi ke `pic.supervisor`
  (atau kepala unit) setelah `ESCALATION_DAYS_OVERDUE` hari.
- **Idempoten** lewat `ReminderLog` unique `(task, kind, days_offset, due_date, recipient, channel)`; tenggat berubah = kunci baru.
- Gagal kirim → status FAILED + `error`; di-retry pada run berikutnya (bukan run yang sama). Tugas tertutup tidak diingatkan.
- Jalankan: Celery beat `notifications.tasks.run_daily_reminders` (jam `EOFFICE_REMINDER_HOUR`) atau `manage.py send_reminders --date YYYY-MM-DD`.

## Celery — PERINGATAN
Redis host dipakai aplikasi lain (db 0, antrean `celery`). E-Office **wajib** `CELERY_BROKER_URL=redis://localhost:6379/5`,
`CELERY_TASK_DEFAULT_QUEUE=eoffice`, worker `-Q eoffice`. Worker yang tersambung ke antrean bersama akan mengambil dan membuang task
aplikasi lain (pernah terjadi: 114 task berkasdigital hilang). Periksa broker/antrean sebelum menyalakan worker.

## Notifikasi
Hanya kanal internal (`Notification`). Email/WhatsApp butuh persetujuan (PRD 6.6). Pesan untuk objek Rahasia tanpa judul/isi.
