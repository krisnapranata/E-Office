---
name: django-permission-security
description: Role, permission, akses per unit, klasifikasi dokumen (Biasa/Terbatas/Rahasia), unggahan/unduhan berizin, dan pengujian akses E-Office. Pakai saat menambah view/endpoint, mengubah siapa boleh melihat/mengubah data, atau menangani dokumen.
---

# Hak akses & keamanan E-Office

## Peran (`accounts.models.Role`)
DIREKTUR, WADIR, KEPALA_UNIT, STAF, SEKRETARIS, ARSIP, ADMIN, AUDITOR. Unit kerja berhierarki (`OrganizationUnit.parent`);
`managed_unit_ids(user)` = unit WADIR/KEPALA_UNIT beserta sub-unitnya.

## Lokasi aturan
| Berkas | Isi |
|---|---|
| `accounts/permissions.py` | peran → kemampuan (`can_issue_instruction`, `can_dispose`, `can_assign_task`, ...), `require()` |
| `workflow/access.py` | `visible_tasks`, `can_view_task`, `can_report_progress`, `can_manage_task`, `can_verify` |
| `letters/services.py`, `instructions/services.py` | `visible_letters`, `visible_dispositions`, `visible_instructions`, ... |
| `agenda/services.py`, `notulen/services.py` | `visible_events`, `can_manage_event`, `can_write_minutes`, `can_approve` (pimpinan rapat) |
| `arsip/services.py` | `visible_archives` + `can_view_archive` (dokumen bersumber = hak lihat objek asal) |

## Aturan
- Periksa izin **di server**; menyembunyikan tombol bukan kontrol keamanan.
- Objek di luar lingkup → `Http404` (bukan 403) agar ID tidak bisa ditebak. Aksi terlarang atas objek yang terlihat → `PermissionDenied` (403).
- Daftar, detail, unduhan, dashboard, dan laporan memakai fungsi `visible_*` yang **sama**, supaya angka dashboard = isi daftar.
- **Rahasia**: hanya pihak terlibat (pembuat, PIC, kolaborator, verifikator, penerima) dan Direktur. Kepala unit/Wadir/Auditor tidak.
  Isi rahasia tidak boleh muncul di notifikasi, log aplikasi, pesan error, atau URL (`notifications.services._task_label`).
- Auditor hanya baca: semua service tulis harus menolak AUDITOR (lihat `can_manage_task`).
- Unggahan: `accounts.files.validate_upload` (ekstensi + ukuran dari settings), nama acak, simpan di `MEDIA_ROOT`. Tidak ada URL media publik;
  unduh lewat view yang memanggil `can_view_*` lalu `audit.log(..., "...download", ...)`.
- POST untuk semua aksi pengubah (CSRF aktif); logout juga POST.
- Kredensial tidak pernah di kode/templat/skill; hanya `.env`.

## Test wajib untuk setiap endpoint baru (PRD 18.8)
Uji **diizinkan dan ditolak**: pengguna unit lain (404), peran tanpa hak (403), auditor (403 untuk tulis), objek Rahasia untuk kepala unit (404),
serta unduhan berkas. Pola ada di `dashboard/tests/test_integration.py::PermissionTests`.
