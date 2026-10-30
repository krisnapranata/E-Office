# E-Office Terintegrasi — Direktur Rumah Sakit

Implementasi `PRD_EOffice_Terintegrasi_Direktur_RS.md` — **12 modul** (Tahap 1–3 inti):

| No | Modul | Menu | Isi |
|---|---|---|---|
| 1 | E-Surat | Surat Masuk / Surat Keluar | nomor otomatis, klasifikasi, lampiran terlindungi |
| 2 | E-Disposisi | Disposisi | arahan, penerusan berjenjang, tugas tertaut |
| 3 | E-Instruksi | Instruksi | draf → terbit, penerima, status baca, atas nama |
| 4 | E-Task Management | Tugas & Monitoring | PIC, kolaborator, bukti, verifikasi |
| 5 | E-Monitoring | Tugas & Monitoring | filter, hambatan, minta pembaruan, ubah PIC/tenggat |
| 6 | E-Reminder | (otomatis) | H-2, terlambat, eskalasi, pengingat agenda |
| 7 | E-Agenda | Agenda | jadwal, undangan, perubahan, bahan, kalender |
| 8 | E-Notulen & Keputusan | Notulen & Keputusan | notulen, butir keputusan, persetujuan pimpinan rapat, cetak |
| 9 | E-Follow Up | Tindak Lanjut | tugas dari keputusan rapat, ringkasan per rapat/unit, cetak belum selesai |
| 10 | E-Arsip | E-Arsip | arsip otomatis + manual, metadata, versi, retensi, pemusnahan berjenjang |
| 11 | E-Reporting | Laporan | per periode/unit/PIC/jenis/status, Excel, cetak/PDF, simpan ke arsip |
| 12 | Executive Dashboard | Dashboard | kartu status, agenda, tindak lanjut rapat, kinerja unit |

Ditambah pengguna/peran/unit, audit trail, dan halaman **Panduan** (per modul dan per peran).

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

### Akun demo (data sintetis)

`python manage.py seed_demo --password 'EofficeDemo#2026'` membuat unit dan akun berikut:

| Username | Peran | Unit |
|---|---|---|
| `direktur` | Direktur | DIR |
| `sekretaris` | Sekretaris/Admin Direktur | DIR |
| `wadir` | Wakil Direktur/Manajer | YANMED |
| `ka_igd` | Kepala Unit | IGD |
| `staf_igd` | Staf/PIC | IGD |
| `ka_farmasi` | Kepala Unit | FARM |
| `staf_farmasi` | Staf/PIC | FARM |
| `arsip` | Petugas Arsip | UMUM |
| `auditor` | Auditor/Reviewer | DIR |

Semua memakai password **`EofficeDemo#2026`**, yang sebaiknya diganti (jalankan ulang `seed_demo --password ...`
atau ubah lewat `/admin/`). Akun demo hanya untuk pengembangan/uji coba — **jangan** dibuat di server produksi.
Panduan setup venv, Docker, test, dan backup ada di README ini.

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

### Deploy ke server (clone pertama) dan Mode Demo

```bash
git clone https://github.com/krisnapranata/E-Office.git && cd E-Office
cp .env.example .env               # isi DJANGO_SECRET_KEY, DB_*, ALLOWED_HOSTS, dan EOFFICE_DEMO_PASSWORD
docker compose up -d --build       # migrate + struktur RSI Yatofa + data demo (Mode Demo, sekali saja)
docker compose exec web python manage.py createsuperuser   # admin ASLI, wajib untuk reset nanti
```

- Instalasi baru berjalan dalam **Mode Demo** (`EOFFICE_MODE_AWAL=DEMO`): saat container start,
  `demo_otomatis` memuat 69 akun `demo_*` (sandi = `EOFFICE_DEMO_PASSWORD`) dan contoh isian semua
  alur, **hanya bila belum ada**. Restart/update tidak menggandakan data.
- Menjelang launching: login dengan admin asli → **Pengaturan Aplikasi** → ketik `RESET DATA DEMO`
  → **Reset data demo**. Semua data demo beserta berkasnya dihapus, mode menjadi **Produksi**, dan
  build/update berikutnya **tidak** memuat data demo lagi (mode tersimpan di database). Bila ada
  data asli yang masih merujuk akun demo, reset dibatalkan seluruhnya dan datanya disebutkan.
- Update: `git pull && docker compose up -d --build`.

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

Cakupan: unit test aturan tugas/reminder/instruksi/disposisi dan integration test HTTP
(permission diizinkan & ditolak, unduhan bukti, konsistensi angka dashboard, alur instruksi →
verifikasi, alur surat → disposisi → tugas).

### Uji end-to-end (pola casemix, skill `uji-e2e`)

| Lapis | Perintah | Isi |
|---|---|---|
| 1 — test client, DB dev, rollback | `.venv/bin/python tools/e2e/jalankan.py [--semua] [--modul X]` | 45 skenario: semua menu + tautannya, semua rute tanpa parameter × 8 peran, alur CRUD (instruksi, surat/disposisi, tugas, akses & kerahasiaan, dashboard, reminder, notifikasi, agenda, notulen & tindak lanjut, arsip, laporan, panduan) |
| 2 — browser, runserver | `KEY=$(.venv/bin/python tools/e2e/browser/sesi.py --user direktur)`<br>`node tools/e2e/browser/e2e.cjs --sesi $KEY --hp`<br>`.venv/bin/python tools/e2e/browser/sesi.py --hapus $KEY` | Klik setiap menu sidebar, console error, 5xx, aset 404, sidebar hover/pin, lebar HP 390 px. POST dibatalkan |
| 2b — alur penuh di browser, DB test | `E2E_BROWSER=1 DJANGO_SETTINGS_MODULE=config.settings.test .venv/bin/python manage.py test tools.e2e.browser` | Login → instruksi → PIC terima/progres/bukti/kirim → verifikasi → dashboard, termasuk POST |
| Gerbang | `.venv/bin/python tools/e2e/katalog.py --cek` | Gagal bila ada menu/rute baru tanpa skenario |
| Rencana | `.venv/bin/python tools/e2e/katalog.py --rencana` | File baru di `docs/rencana-uji/` (tidak pernah menimpa) |

Lapis 1 berjalan di DB dev tetapi setiap skenario di-rollback: akun/unit QA (`qa_*`) dibuat di dalam
transaksi, unggahan ke folder sementara, DDL diblokir, jaringan luar dan Celery dicegat. Lapis 2 memakai
patchright dari ekstensi CodeGPT (atau `E2E_PATCHRIGHT=/path`), tanpa `npm install`.

## Konfigurasi aturan bisnis (PRD Bab 16)

| Variabel | Default | Keterangan |
|---|---|---|
| `EOFFICE_INSTRUCTION_ISSUER_ROLES` | `DIREKTUR,WADIR,SEKRETARIS` | Peran yang boleh membuat instruksi |
| `EOFFICE_REMINDER_DAYS_BEFORE` | `2` | Contoh `2,1` untuk H-2 dan H-1 (hari kalender) |
| `EOFFICE_ESCALATION_DAYS_OVERDUE` | `3` | Eskalasi ke atasan PIC (atau kepala unit) |
| `EOFFICE_REMINDER_HOUR` | `7` | Jam job pengingat harian (zona `TIME_ZONE`) |
| `EOFFICE_AGENDA_REMINDER_DAYS` | `1,0` | Pengingat agenda H-1 dan hari-H |
| `EOFFICE_RETENTION_YEARS` | `DEFAULT=5` | Retensi arsip per jenis, mis. `DEFAULT=5,SURAT_MASUK=10` |

Default yang perlu dikonfirmasi rumah sakit (PRD Bab 16): notulen disetujui **pimpinan rapat** (penyelenggara
agenda); keputusan menjadi tugas **setelah** notulen disetujui; pemusnahan arsip **diusulkan Petugas Arsip,
disetujui Direktur**, hanya setelah masa retensi; klasifikasi *Terbatas* saat ini diperlakukan seperti *Biasa*.

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
| `uji-e2e` | E2E pola casemix: lapis 1 (rollback DB dev), lapis 2/2b (browser), gerbang katalog, rencana uji; aturan menu/rute baru = skenario baru |
| `emboss-blue-glass-theme` | Tema Emboss Blue Glass, kontrak markup shell, area kertas, halaman login |

Pemeliharaan: perbarui skill bersamaan dengan perubahan aturan yang dijelaskannya; hindari dua skill dengan cakupan sama.

## Panduan pengguna

Menu **Panduan** (`/panduan/`) tersedia untuk semua pengguna: alur besar, panduan langkah demi langkah per peran
(peran pengguna tampil pertama), arti status & penanda, tampilan, keamanan, dan tanya-jawab. Isinya ada di
`panduan/konten.py` (data, bukan templat) — nama tombol harus sama dengan templat, dan nilai konfigurasi
(H-n, eskalasi, jam pengingat, berkas, penerbit instruksi) dibaca dari settings. **Ubah alur/tombol = perbarui
`panduan/konten.py`.**

## Tampilan

Tema **Emboss Blue Glass (Kaca Biru Timbul)**: `static/css/tema/emboss-blue-glass.css` → `blue-glass.css` → `mint-forest.css`
(disalin dari proyek casemix), shell sidebar navy + topbar, dan halaman login yang sama dengan casemix. Detail di skill
`emboss-blue-glass-theme`.

## Backlog berikutnya

- Kanal notifikasi email/WhatsApp (menunggu persetujuan, PRD 6.6).
- Tanda tangan elektronik tersertifikasi (di luar cakupan MVP).
- Pola nomor surat/instruksi yang dapat dikonfigurasi; jenis surat internal.
- Pipeline CI dan lint.
