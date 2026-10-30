---
name: uji-e2e
description: "Uji END-TO-END E-Office (pola casemix) + aturan WAJIB: setiap menu/halaman/rute BARU harus punya skenario e2e. Lapis 1 tools/e2e/jalankan.py (Django test client, DB dev, setiap skenario di-ROLLBACK, dunia QA qa_* dibuat di dalam transaksi, DDL diblokir, unggahan ke folder sementara, jaringan luar & Celery dicegat). Lapis 2 tools/e2e/browser/e2e.cjs (patchright ke runserver; klik menu, console error, HP 390px; POST dibatalkan). Lapis 2b test_alur.py + alur.cjs (alur penuh di browser termasuk POST, LiveServer + DB test). Gerbang katalog.py --cek dan rencana uji bertanggal di docs/rencana-uji/ (selalu FILE BARU). Gunakan SETIAP KALI menambah menu sidebar/halaman/URL/endpoint/form, atau saat diminta e2e, uji semua menu, regression, rencana uji, sebelum deploy, atau saat katalog.py --cek merah."
---

# Uji end-to-end (e2e) E-Office

Pola sama dengan casemix (`/home/krisna/iDRG/casemix/casemixiDRG/.claude/skills/uji-e2e`), disesuaikan:
semua tabel E-Office InnoDB milik Django, autentikasi Django (bukan sesi Khanza), dan Redis host dipakai bersama.

## Aturan wajib (setiap perubahan yang menambah menu/rute)
1. **Menu/rute baru = skenario baru** di `tools/e2e/skenario/<modul>.py` dengan `menu=["app:nama_url", ...]`.
   Menulis data → `crud=True` dan buktikan lewat ORM bahwa data benar berubah (status, relasi, audit).
   Hanya membuka halaman → cukup tanpa `crud`. Rute tanpa parameter sudah dijelajah otomatis untuk 8 peran.
2. Jalankan: `.venv/bin/python tools/e2e/jalankan.py --modul <modul>` → semua OK. Sebelum selesai: `--semua`.
3. Gerbang: `.venv/bin/python tools/e2e/katalog.py --cek` → `[OK]`. Bila `[INFO] ... kini tercakup` →
   `--perbarui-baku` (backlog menyusut). JANGAN `--perbarui-baku` untuk meloloskan rute baru tanpa skenario.
   Menu yang benar-benar hanya-baca (dashboard, panduan) didaftarkan di `HANYA_BACA` pada `katalog.py` — tetap
   wajib punya skenario, cukup tanpa `crud`.
4. Menu sidebar baru / perubahan tampilan → lapis 2 (`e2e.cjs --hp`). Alur kritis baru → perluas lapis 2b.
5. **Rencana**: `.venv/bin/python tools/e2e/katalog.py --rencana` → file BARU `docs/rencana-uji/<tanggal>-rencana-e2e[-vN].md`
   + baris di `INDEX.md`. File lama tidak pernah diubah. Buat versi baru setiap selesai menambah menu/skenario.
6. Unit/integration test Django (`manage.py test`) tetap wajib untuk aturan bisnis — e2e tidak menggantikannya.

## Menulis skenario (lapis 1)
```python
from . import skenario
from ._bantu import JUDUL_QA, berkas, hari, url

@skenario("tugas", "Penugasan langsung → selesai", menu=["workflow:create"], crud=True, role="ka_igd")
def _(u):
    u.get(url("workflow:create"), ada=["Penugasan langsung"])          # 200 + teks harus ada
    u.post(url("workflow:create"), {"title": f"{JUDUL_QA} X", ...}, harap=302)   # CSRF otomatis
    t = Task.objects.get(title=f"{JUDUL_QA} X")
    u.sebagai("staf_igd")                                               # ganti pengguna (force_login)
    u.post(url("workflow:evidence", t.pk), {"file": berkas()}, harap=302)
    u.post(url("workflow:submit", t.pk), harap=200, follow=True, ada=["..."])   # cek pesan galat
    u.harap(t.status == ..., "pesan")
```
- `u.w` = dunia QA (`World("qa_")`): `u.w.direktur`, `sekretaris`, `wadir`, `ka_igd`, `staf_igd`, `ka_farmasi`,
  `staf_farmasi`, `auditor`, `arsip`, unit `u.w.igd/farmasi/yanmed/dir_unit`. Dibuat ulang tiap skenario, dibuang oleh rollback.
- `u.get/post(url, harap=200|(200,302)|None, ada=[teks], tidak_ada=[teks])` — gagal otomatis bila dialihkan ke
  login, HTTP tak sesuai, atau halaman memuat Traceback/TemplateSyntaxError/NoReverseMatch.
- `u.keluar()` untuk uji tanpa login; set `u.pengguna = None` sebelum POST yang memang mengalihkan ke login (logout).
- `u.p.celery` (task dicegat), `u.p.jaringan` (host luar dicoba), `u.p.tulis` (tabel ditulis); `u.catatan.append(...)`.
- Waktu dikendalikan: `run_reminders(today)` / `call_command("send_reminders", "--date", ...)`.
- DB dev berisi data lain (akun demo, tugas demo): bandingkan **selisih** atau pakai peran berlingkup unit QA
  (`ka_igd`, `ka_farmasi`) untuk angka pasti. Data uji berjudul `JUDUL_QA` ("QA E2E ...").
- Pesan galat validasi form mengikuti terjemahan Django — asersikan `alert-danger` + data tidak berubah, bukan teks bawaan.

## Pengaman (`tools/e2e/_dasar.py`)
- Menolak jalan dengan `config.settings.prod` / `DEBUG=False`. Transaksi `default` di-rollback per skenario,
  savepoint per permintaan.
- DDL & tulis ke tabel non-InnoDB diblokir. `MEDIA_ROOT` → folder sementara; hasher password cepat untuk akun QA.
- Jaringan luar → `JaringanDiblokir`. Celery `apply_async/delay` dicegat — **penting**: Redis host dipakai aplikasi
  lain; worker/broker tidak boleh tersentuh uji.
- Verifikasi bahwa rollback bersih: hitung baris per model sebelum/sesudah, cek tidak ada `qa_*`/`QA_*`/"QA E2E".
  ID auto-increment yang melompat itu normal (InnoDB tidak me-rollback counter).

## Lapis 2 (browser, runserver dev)
```bash
.venv/bin/python manage.py runserver 127.0.0.1:8011            # 8090 dipakai container
KEY=$(.venv/bin/python tools/e2e/browser/sesi.py --user direktur)   # akun dari seed_demo; tanpa password
node tools/e2e/browser/e2e.cjs --sesi $KEY [--hp] [--layar DIR] [--hanya /tugas/] [--base URL]
.venv/bin/python tools/e2e/browser/sesi.py --hapus $KEY
```
Klik setiap menu di `aside#sidebar` (URL, `.active`, h1, isi `#workspace`), console error, 5xx, aset static 404,
sidebar melebar & pin, `--hp`: tanpa scroll samping di 390 px + offcanvas. POST dibatalkan.
Jebakan: runserver `--noreload` menyimpan templat di cache — restart setelah mengubah templat. Jangan `pkill -f`
dengan pola yang juga ada di baris perintah sendiri (mematikan shell); hentikan lewat PID port.
patchright dicari dari ekstensi CodeGPT (`_patchright.cjs`) atau `E2E_PATCHRIGHT`.

## Lapis 2b (alur penuh di browser, DB test)
```bash
E2E_BROWSER=1 DJANGO_SETTINGS_MODULE=config.settings.test .venv/bin/python manage.py test tools.e2e.browser --noinput
# + E2E_LAYAR=/folder untuk screenshot tiap tahap
```
`StaticLiveServerTestCase` membuat dunia `e2e_*` (nama tampilan = username) dengan password acak (env `E2E_SANDI`),
lalu `alur.cjs` login lewat form (`#username/#password/#leTombol`), membuat & menerbitkan instruksi, PIC menerima,
melapor, mengunggah bukti, mengirim, Direktur memverifikasi, kartu dashboard "Selesai" membuka daftar berisi tugas.
Pilih opsi select secara TEPAT (label/kode), bukan opsi pertama. Tanpa `E2E_BROWSER=1` test dilewati (suite tetap cepat).

## Temuan yang sudah diketahui
`tools/e2e/diketahui.py`: URL yang gagal karena bug yang belum diperbaiki → "DIKETAHUI", tidak menggagalkan.
Setelah diperbaiki, hapus barisnya. Kegagalan BARU tidak boleh dimasukkan tanpa persetujuan user.

## Angka baku (2026-10-30, DB dev)
Lapis 1 `--semua`: 51 skenario, ±1100 permintaan, ±24 dtk, 0 gagal · katalog: 89 rute, 89 tercakup, backlog 0 ·
lapis 2: 29 pemeriksaan, 0 gagal · lapis 2b: 2 alur (instruksi 15 langkah + pengguna 17 langkah), ±11 dtk.
Menu khusus peran (Pengguna, Pengaturan Aplikasi = ADMIN) dijelajah crawler sebagai peran itu lewat `MENU_PERAN` di `otomatis.py`.
DB dev berisi data demo (`demo_*`, 69 akun): skenario jangan mengandaikan unit kosong/tanpa kepala. Temuan yang sudah diperbaiki: tabel daftar tanpa `.table-responsive` (scroll samping
di HP); status baca instruksi tidak tercatat saat PIC bekerja dari halaman tugas.
