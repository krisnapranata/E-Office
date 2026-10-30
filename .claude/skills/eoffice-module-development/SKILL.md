---
name: eoffice-module-development
description: Pola menambah/mengubah modul E-Office (mis. E-Agenda, E-Notulen, E-Follow Up, E-Arsip, E-Reporting) agar terintegrasi dengan Task, notifikasi, audit, dan hak akses. Pakai saat membuat app/fitur baru atau menghubungkan modul ke mesin tugas.
---

# Pengembangan modul E-Office

Prinsip PRD Bab 12 & 17: **satu sistem, satu model Task** sebagai pusat monitoring. Modul lain adalah *sumber* pekerjaan.

## Langkah membuat modul baru
1. Baca PRD bagian modulnya (Bab 6.x) dan tahapnya (Bab 14). Catat asumsi yang belum divalidasi (Bab 16).
2. Buat app sendiri: `models.py`, `services.py` (semua tulis data), `forms.py`, `views.py` (tipis), `urls.py` (pakai `app_name`), `admin.py`, `tests/`.
   Daftarkan di `INSTALLED_APPS` dan `config/urls.py`; tambah menu di `templates/partials/_sidebar_menu.html` (ikon `bi-*` di `span.sidebar-icon`).
3. Bila modul menghasilkan pekerjaan → **jangan buat model tugas sendiri.** Panggil `workflow.services.create_task(...)` dengan:
   - `source_type` dari `workflow.models.TaskSource` (tambah pilihan baru + migrasi bila perlu),
   - FK ke objek sumber di `Task` (lihat pola `instruction`/`disposition`) + `UniqueConstraint` anti-duplikasi,
   - `verifier` = pejabat yang berwenang menutup.
   Contoh nyata: `instructions/services.py::issue`, `letters/services.py::create_disposition`.
4. Status objek sumber yang mengikuti tugas → sinkronkan dari `workflow.services._on_closed` (pola `sync_disposition_status`).
5. Notifikasi lewat `notifications/services.py` (tambah fungsi baru di sana; label rahasia via `_task_label`). Audit lewat `audit.services.log(user, "modul.aksi", obj, **perubahan)`.
6. Hak akses: buat `visible_<objek>(user)` + `can_<aksi>(user, obj)`; view mengembalikan **404** untuk objek di luar lingkup. Lihat skill `django-permission-security`.
7. Unggahan: `FileField(upload_to=accounts.files.protected_upload_to(...), validators=[validate_upload])` dan unduh via view berizin + audit.
8. Dashboard: angka baru harus dihitung dari queryset lingkup pengguna dan menaut ke daftar dengan filter yang sama (`dashboard/services.py`).
9. Template extend `base.html`, judul `<h1 class="h3">`, isi dalam `.card`. Ikuti skill `emboss-blue-glass-theme`.
10. Test: unit untuk aturan, integration untuk izin diizinkan/ditolak, tambah skenario E2E bila alur kritis (skill `eoffice-e2e-testing`).

## Jangan
- Duplikasi tugas di tabel modul (PRD 6.9: "Menghindari pencatatan tugas yang sama secara terpisah").
- Mengubah status Task langsung (`task.status = ...`); selalu lewat `workflow/services.py`.
- Refactor modul lain yang tidak terkait.
