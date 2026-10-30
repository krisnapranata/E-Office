# E-Office Terintegrasi — Direktur Rumah Sakit

Implementasi MVP (PRD Bab 13) dari `PRD_EOffice_Terintegrasi_Direktur_RS.md`:
pengguna/peran/unit, E-Surat, E-Disposisi, E-Instruksi, E-Task Management, E-Monitoring,
E-Reminder (H-2, terlambat, eskalasi), Executive Dashboard, dan audit trail.

Stack: Django 5.2 · MariaDB/MySQL · Bootstrap 5 + Bootstrap Icons + HTMX (disajikan lokal, tanpa CDN) · tema Emboss Blue Glass ·
Celery + Redis · Gunicorn · Docker (port **8090**).

## Arsitektur modul

| App | Tanggung jawab |
|---|---|
| `accounts` | User (peran, unit, atasan), unit kerja, aturan hak akses (`permissions.py`), validasi unggahan |
| `audit` | `AuditLog` append-only + `audit.services.log()` |
| `letters` | Surat masuk/keluar, disposisi (termasuk penerusan) |
| `instructions` | Instruksi Direktur, penerima & status baca |
| `workflow` | **Task** sebagai pusat monitoring lintas modul, mesin status (`services.py`), lingkup akses (`access.py`), bukti & verifikasi |
| `notifications` | Notifikasi internal, `ReminderLog` idempotent, job Celery harian |
| `dashboard` | Executive Dashboard; setiap angka tertaut ke daftar tugas terfilter |

Aturan inti:
- Disposisi yang memerlukan tindakan dan setiap penerima instruksi menghasilkan tepat satu `Task`
  yang menyimpan tautan ke sumbernya (dijaga unique constraint).
- Semua perubahan status melewati `workflow/services.py` (`ALLOWED_TRANSITIONS`).
  Progres 100% **tidak** menutup tugas; penutupan lewat kirim hasil → verifikasi.
- "Terlambat" bukan status tersimpan, melainkan dihitung: tenggat < hari ini dan tugas belum Selesai/Dibatalkan.
- Akses diperiksa di server; objek di luar lingkup pengguna mengembalikan 404 (URL tidak bisa ditebak).
  Klasifikasi **Rahasia** hanya untuk pihak yang terlibat dan Direktur; isi tidak muncul di notifikasi.
- Berkas disimpan di `MEDIA_ROOT` dengan nama acak dan hanya dapat diunduh lewat view berizin.

### Status tugas
`DRAF → MENUNGGU_PENERIMAAN → BELUM_DIMULAI → BERJALAN ⇄ TERHAMBAT → MENUNGGU_VERIFIKASI → SELESAI`,
`MENUNGGU_VERIFIKASI → PERLU_PERBAIKAN → BERJALAN/MENUNGGU_VERIFIKASI`, dan pembatalan (dengan alasan)
dari status terbuka mana pun.

## Pengembangan lokal (wajib `venv`)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # isi DJANGO_SECRET_KEY, DB_*, CELERY_BROKER_URL
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo --password 'GantiPasswordDemo'   # opsional, data sintetis
python manage.py runserver 0.0.0.0:8090
```

Worker/beat (opsional di dev; default dev menjalankan task secara eager):
```bash
celery -A config worker -Q eoffice -l info
celery -A config beat -l info
```

Menjalankan pengingat manual (mis. untuk uji tanggal tertentu):
```bash
python manage.py send_reminders --date 2026-11-02
```

## Docker (port 8090)

`docker-compose.yml` menjalankan `web` (Gunicorn, port 8090), `worker`, dan `beat` dengan
`network_mode: host` sehingga `DB_HOST=localhost` dan Redis `localhost` di `.env` merujuk ke
MariaDB/Redis di host.

```bash
docker compose up -d --build        # web menjalankan migrate otomatis (RUN_MIGRATIONS=1)
docker compose exec web python manage.py createsuperuser
curl http://localhost:8090/healthz
docker compose logs -f web worker beat
```

> Celery memakai DB Redis dan antrean khusus (`redis://localhost:6379/5`, antrean `eoffice`).
> Jangan arahkan ke DB/antrean yang dipakai aplikasi lain: worker akan mengonsumsi dan membuang
> task yang tidak dikenalnya.

Image hanya berisi dependensi dari `requirements.txt`, berjalan sebagai user non-root, dan
memerlukan `DJANGO_SECRET_KEY` saat runtime (`config.settings.prod`). HTTPS diterminasi di reverse
proxy (Nginx); setelah TLS aktif set `DJANGO_SECURE_SSL_REDIRECT=true` dan `DJANGO_SECURE_COOKIES=true`.

## Pengujian

```bash
source .venv/bin/activate
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test            # semua
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test notifications  # subset
```
Test memakai engine database dari `.env` tetapi Django membuat database terpisah
`test_<DB_NAME>`; database development/produksi tidak tersentuh. Data uji sintetis ada di
`testutils/factories.py`. Waktu dikendalikan dengan parameter `today` pada `run_reminders`.

Cakupan saat ini: unit test aturan tugas/reminder/instruksi/disposisi dan integration test
HTTP (permission diizinkan & ditolak, unduhan bukti, konsistensi angka dashboard, alur instruksi
→ verifikasi, alur surat → disposisi → tugas). **Belum ada E2E browser (Playwright)** — lihat
backlog di bawah.

## Konfigurasi aturan bisnis (PRD Bab 16)

| Variabel | Default | Keterangan |
|---|---|---|
| `EOFFICE_INSTRUCTION_ISSUER_ROLES` | `DIREKTUR,WADIR,SEKRETARIS` | Peran yang boleh membuat instruksi |
| `EOFFICE_REMINDER_DAYS_BEFORE` | `2` | Contoh `2,1` untuk H-2 dan H-1 (hari kalender) |
| `EOFFICE_ESCALATION_DAYS_OVERDUE` | `3` | Eskalasi ke atasan PIC (atau kepala unit) |
| `EOFFICE_REMINDER_HOUR` | `7` | Jam job pengingat harian (zona `TIME_ZONE`) |

## Backup & restore

```bash
mysqldump -u <user> -p --single-transaction eoffice > eoffice-$(date +%F).sql
docker run --rm -v e-office_eoffice_media:/m -v "$PWD":/b alpine tar czf /b/media-$(date +%F).tgz -C /m .
# restore
mysql -u <user> -p eoffice < eoffice-YYYY-MM-DD.sql
docker run --rm -v e-office_eoffice_media:/m -v "$PWD":/b alpine tar xzf /b/media-YYYY-MM-DD.tgz -C /m
```
Uji pemulihan wajib dilakukan sebelum produksi (PRD 13). Rollback migrasi:
`python manage.py migrate <app> <migrasi_sebelumnya>` setelah backup.

## Skill agent

Lokasi: `.claude/skills/<nama>/SKILL.md` (Claude Code). Periksa skill relevan sebelum mengerjakan tugas (PRD 18.2).

| Skill | Cakupan |
|---|---|
| `django-project-standards` | venv, struktur app, settings, `.env`, aset tanpa CDN, Docker port 8090 |
| `eoffice-module-development` | Pola modul baru dan integrasinya dengan Task, notifikasi, audit, izin |
| `django-model-migration` | Model, migrasi, keterbatasan MariaDB, transaksi |
| `django-permission-security` | Peran, lingkup unit, klasifikasi Rahasia, unggah/unduh berizin, uji akses |
| `eoffice-workflow` | Mesin status, bukti/verifikasi, reminder idempotent, isolasi antrean Celery |
| `eoffice-e2e-testing` | Unit/integration/E2E, data sintetis, waktu terkendali, verifikasi visual |
| `emboss-blue-glass-theme` | Tema Emboss Blue Glass, kontrak markup shell, area kertas, halaman login |

Pemeliharaan: perbarui skill bersamaan dengan perubahan aturan yang dijelaskannya; hindari dua skill dengan cakupan sama.

## Tampilan

Tema **Emboss Blue Glass (Kaca Biru Timbul)**: `static/css/tema/emboss-blue-glass.css` → `blue-glass.css` → `mint-forest.css`
(disalin dari proyek casemix), shell sidebar navy + topbar, dan halaman login yang sama dengan casemix. Detail di skill
`emboss-blue-glass-theme`.

## Backlog berikutnya

- E2E Playwright untuk 10 skenario PRD 18.4 C (saat ini skenario 1, 2, 7, 9 dicakup level HTTP).
- Tahap 2: E-Agenda, E-Notulen & Keputusan, E-Follow Up, E-Arsip lanjutan.
- Tahap 3: E-Reporting & ekspor PDF/Excel, kanal email/WhatsApp.
- Pipeline CI dan lint.
