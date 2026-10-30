---
name: django-model-migration
description: Aturan model, migrasi, integritas data, transaksi, dan prosedur perubahan skema E-Office di MariaDB/MySQL. Pakai setiap kali mengubah models.py, membuat/menjalankan migrasi, atau menambah constraint/index.
---

# Model & migrasi E-Office

## Wajib
- Skema hanya berubah lewat migrasi Django. Tidak ada `ALTER TABLE` manual.
- Setelah ubah model:
  ```bash
  .venv/bin/python manage.py makemigrations <app> -n <nama_deskriptif>
  .venv/bin/python manage.py check --database default
  .venv/bin/python manage.py makemigrations --check --dry-run
  DJANGO_SETTINGS_MODULE=config.settings.test .venv/bin/python manage.py test --noinput
  ```
  Baca berkas migrasi yang dihasilkan sebelum melaporkan.
- Migrasi destruktif (hapus kolom/tabel, ubah tipe yang memotong data, `RemoveField` pada data resmi) **butuh rencana, backup, dan persetujuan pengguna** (PRD 18.1 no. 9). Untuk data migration pakai `RunPython` dengan fungsi `reverse`.

## Keterbatasan MariaDB (DB produksi: MariaDB 10.11)
- **Unique constraint bersyarat (`condition=`) tidak didukung** — Django memberi `models.W036` dan constraint *tidak dibuat*.
  Gunakan unique biasa: unique index MySQL/MariaDB memperlakukan NULL sebagai berbeda, jadi FK sumber yang nullable tetap aman
  (contoh: `uniq_task_per_instruction_target`, `uniq_task_per_disposition` di `workflow/models.py`).
- Index fungsional/ekspresi terbatas; utamakan `models.Index(fields=[...])` untuk pola filter dashboard (`unit,status`, `pic,status`).
- Charset `utf8mb4`.

## Integritas
- FK ke data resmi memakai `on_delete=models.PROTECT`. Penghapusan permanen dibatasi; admin data resmi menolak delete.
- `AuditLog` append-only: `save()` pada baris lama dan `delete()` melempar `ValueError`. Jangan tambah jalur update.
- Operasi yang mengubah beberapa objek: `@transaction.atomic` di service. Gunakan `select_for_update()` saat membaca-lalu-mengubah status yang bisa diproses paralel (contoh `instructions.services.issue`, `notifications.services._deliver`).
- Penomoran (`config/numbering.py`) bergantung pada field `unique`; tangani tabrakan bila volume tinggi.

## Deployment migrasi
- Container `web` menjalankan `migrate` saat start (`RUN_MIGRATIONS=1`). Backup DB sebelum rilis yang memuat migrasi.
- Rollback: `python manage.py migrate <app> <migrasi_sebelumnya>` setelah backup; sebutkan di laporan bila migrasi tidak reversible.
