---
name: django-project-standards
description: Standar proyek Django E-Office — venv, struktur app, settings dev/test/prod, .env, aset statis tanpa CDN, Docker port 8090, perintah test. Pakai sebelum menambah dependensi, mengubah settings/urls, menjalankan server/test, atau menyentuh Dockerfile/docker-compose.
---

# Standar proyek Django E-Office

Sumber kebenaran: `PRD_EOffice_Terintegrasi_Direktur_RS.md` (Bab 12, 12.1, 18) dan `README.md`.

## Lingkungan
- Python 3.12, Django 5.2 LTS. Selalu pakai venv `.venv/` — jangan `pip install` ke Python sistem.
  Dari agent (shell tidak persisten) panggil langsung `.venv/bin/python` / `.venv/bin/pip`.
- Dependensi dipatok di `requirements.txt` (`paket==versi`). Tambah dependensi = pasang di venv, patok versi, sebutkan di laporan.
- Rahasia hanya di `.env` (di-`.gitignore`, juga `.dockerignore`). `config/settings/base.py` memuat `.env` tanpa menimpa env yang sudah ada.
  Variabel baru wajib ditambahkan ke `.env.example` tanpa nilai rahasia.

## Settings
| Modul | Dipakai untuk |
|---|---|
| `config.settings.dev` | default `manage.py`; DEBUG, Celery eager |
| `config.settings.test` | test; DB engine dari `.env`, Django membuat `test_<DB_NAME>` |
| `config.settings.prod` | Docker; `DJANGO_SECRET_KEY` wajib, whitenoise manifest |

Aturan bisnis yang masih menunggu validasi (PRD Bab 16) masuk `settings.EOFFICE` + env var, bukan konstanta di kode.

## Struktur app (satu domain = satu app)
`accounts` (user/unit/izin/unggahan) · `audit` · `letters` · `instructions` · `workflow` (Task, pusat) · `notifications` · `dashboard`.
Logika bisnis di `services.py`, aturan akses di `access.py`/`accounts/permissions.py`, view tipis. Jangan taruh logika di template.

## Frontend
Bootstrap 5.3.3, Bootstrap Icons, HTMX disajikan dari `static/vendor/` — **tanpa CDN** dan tanpa inline `<script>`/`onclick`.
JS halaman di `static/js/app.js` (konfirmasi: atribut `data-confirm`). Tema: lihat skill `emboss-blue-glass-theme`.

## Perintah
```bash
.venv/bin/python manage.py check --database default      # termasuk peringatan khusus MariaDB
.venv/bin/python manage.py makemigrations --check --dry-run
DJANGO_SETTINGS_MODULE=config.settings.test .venv/bin/python manage.py test --noinput
.venv/bin/python manage.py runserver 127.0.0.1:8011       # 8090 dipakai container
docker compose up -d --build                              # web :8090, worker, beat
```

## Docker
- `Dockerfile`: python:3.12-slim, user non-root, `collectstatic` saat build, HEALTHCHECK `/healthz`, Gunicorn `0.0.0.0:${PORT:-8090}`.
- `docker-compose.yml`: `network_mode: host` → `DB_HOST=localhost` = MariaDB host. `RUN_MIGRATIONS=1` hanya di `web`.
- Build gagal `MissingFileError` = aset yang dirujuk CSS (mis. `.map`, font) tidak ada di `static/`. Lengkapi asetnya, jangan matikan manifest.
- Jangan tulis kata `url` diikuti kurung di komentar CSS — manifest collectstatic membacanya sebagai rujukan aset.

## Laporan akhir (PRD 18.2)
Ringkasan perubahan, file penting, migrasi, perintah test + hasil apa adanya, risiko, langkah verifikasi manual.
