# PRODUCT REQUIREMENTS DOCUMENT (PRD)
# E-Office Terintegrasi untuk Direktur Rumah Sakit

**Versi:** 1.2  
**Tanggal:** 30 Oktober 2026  
**Status:** Draft untuk validasi proses bisnis dan standar implementasi teknis (MVP Tahap 1 telah diimplementasikan; lihat Bab 22)

## 1. Ringkasan Eksekutif

E-Office Terintegrasi adalah sistem untuk membantu Direktur rumah sakit mengendalikan surat, disposisi, instruksi, pekerjaan, agenda, keputusan rapat, tindak lanjut, arsip, dan evaluasi kinerja unit dalam satu platform.

Sistem terdiri dari 12 modul:
1. E-Surat — surat masuk dan keluar.
2. E-Disposisi — arahan dan distribusi surat.
3. E-Instruksi — pencatatan perintah Direktur.
4. E-Task Management — penugasan, PIC, prioritas, dan tenggat.
5. E-Monitoring — pemantauan progres dan penyelesaian.
6. E-Reminder — pengingat otomatis dan eskalasi.
7. E-Agenda — agenda Direktur, rapat, dan kegiatan.
8. E-Notulen & Keputusan — hasil rapat dan keputusan.
9. E-Follow Up — tindak lanjut pekerjaan.
10. E-Arsip — dokumen dan bukti pekerjaan.
11. E-Reporting — laporan pelaksanaan dan evaluasi unit.
12. Executive Dashboard — ringkasan kendali Direktur.

Prinsip utama: setiap arahan atau keputusan yang memerlukan tindakan harus dapat ditelusuri hingga penanggung jawab, tenggat, progres, bukti pelaksanaan, verifikasi, dan penutupan. Pekerjaan dari disposisi, instruksi, keputusan rapat, maupun penugasan langsung menggunakan mesin tugas dan monitoring bersama agar tidak terjadi duplikasi.

Dokumen ini adalah PRD awal. Alur persetujuan, struktur organisasi, retensi arsip, dan kebijakan eskalasi perlu divalidasi oleh rumah sakit sebelum implementasi produksi.

## 2. Latar Belakang dan Masalah

Pekerjaan administrasi dan tindak lanjut pimpinan dapat tersebar di surat, pesan, dokumen, rapat, dan komunikasi langsung. Hal ini berisiko menyebabkan instruksi tidak tercatat secara terpusat, PIC atau tenggat tidak jelas, status pekerjaan sulit diketahui, keterlambatan baru diketahui setelah tenggat terlewati, keputusan rapat tidak ditindaklanjuti, bukti tersebar, dan laporan harus dibuat manual.

E-Office menyediakan sumber informasi bersama, pemantauan terpusat, notifikasi, dan jejak audit.

## 3. Tujuan Produk

- Menyatukan pengelolaan surat, disposisi, instruksi, agenda, keputusan, dan pekerjaan.
- Memudahkan Direktur melihat pekerjaan berjalan, terlambat, dan membutuhkan keputusan.
- Memastikan pekerjaan memiliki PIC, tenggat, status, dan riwayat.
- Mengirim pengingat otomatis, termasuk H-2 sebelum tenggat.
- Mengelola bukti pelaksanaan dan verifikasi.
- Menyediakan laporan pelaksanaan dan evaluasi unit.
- Mencatat aktivitas penting dalam audit trail.

### Indikator keberhasilan awal
- Semua instruksi resmi yang diterbitkan melalui sistem memiliki pembuat, penerima, dan waktu pencatatan.
- Sebagian besar pekerjaan aktif memiliki PIC dan tenggat yang jelas.
- Pengingat H-2 tercatat pada log notifikasi.
- Direktur dapat melihat daftar pekerjaan terlambat tanpa meminta rekap manual.
- Laporan per periode dapat dihasilkan dari data sistem.
- Perubahan status penting dapat ditelusuri berdasarkan pengguna dan waktu.

## 4. Ruang Lingkup

### Termasuk
- Pengguna, peran, unit kerja, dan hak akses.
- Surat masuk dan keluar.
- Disposisi dan instruksi Direktur.
- Tugas, progres, tenggat, hambatan, bukti, dan verifikasi.
- Pengingat dan eskalasi.
- Agenda, notulen, keputusan rapat, dan tindak lanjut.
- Arsip dokumen.
- Laporan dan dashboard.
- Audit trail.

### Di luar cakupan MVP kecuali disepakati
- Tanda tangan elektronik tersertifikasi.
- Integrasi dengan sistem eksternal.
- Pengelolaan keuangan, pengadaan, inventaris, SDM, atau rekam medis.
- Aplikasi mobile native.
- Penilaian pegawai untuk remunerasi.

## 5. Pengguna dan Hak Akses

| Peran | Tanggung jawab | Hak akses umum |
|---|---|---|
| Direktur | Menerbitkan instruksi, memberi disposisi, memantau pekerjaan | Akses eksekutif sesuai kewenangan |
| Wakil Direktur/Manajer | Mengawasi bidang/unit | Data dalam lingkup kewenangannya |
| Kepala Unit/Instalasi | Membagi dan memantau tugas unit | Pengelolaan tugas dan laporan unit |
| Staf/PIC | Melaksanakan dan melaporkan tugas | Tugas yang ditugaskan kepadanya |
| Sekretaris/Admin Direktur | Administrasi surat, agenda, dan rapat | Modul yang diizinkan |
| Petugas Arsip | Menata metadata dan arsip | Pengelolaan arsip sesuai kewenangan |
| Administrator Sistem | Mengelola konfigurasi dan akun | Administrasi teknis |
| Auditor/Reviewer | Memeriksa data dan jejak audit | Akses baca sesuai lingkup audit |

Akses mengikuti prinsip least privilege. Hak melihat, mengubah, menyetujui, dan mengunduh ditentukan oleh peran, unit, kepemilikan tugas, dan klasifikasi dokumen. Koreksi data resmi harus tercatat; penghapusan permanen dibatasi.

## 6. Kebutuhan Fungsional per Modul

### 6.1 E-Surat
- Mencatat nomor agenda/surat, tanggal, pengirim/penerima, perihal, klasifikasi, tingkat kerahasiaan, ringkasan, dan lampiran.
- Membedakan surat masuk, surat keluar, dan surat internal jika diperlukan.
- Menyediakan pencarian dan filter.
- Menghubungkan surat masuk ke satu atau lebih disposisi.
- Menghubungkan dokumen dengan arsip.
- Menyimpan riwayat perubahan dan mendukung pola nomor otomatis yang dikonfigurasi.

### 6.2 E-Disposisi
- Membuat disposisi dari surat masuk.
- Menentukan pemberi disposisi, penerima, unit, arahan, prioritas, dan tenggat.
- Mencatat status terkirim, dibaca, ditindaklanjuti, dan selesai. Penerimaan pekerjaan dicatat pada tugas tertaut (status *Menunggu penerimaan* → *Belum dimulai*).
- Disposisi yang memerlukan tindakan wajib memiliki tenggat.
- Mengubah disposisi yang membutuhkan tindakan menjadi tugas tertaut.
- Menyimpan riwayat penerusan (disposisi turunan menyimpan tautan ke disposisi asal) dan notifikasi.
- Membatasi akses berdasarkan klasifikasi surat.

### 6.3 E-Instruksi
- Membuat instruksi dengan kode unik, judul, uraian, tanggal, prioritas, klasifikasi, penerima, PIC, tenggat, kriteria selesai, dan lampiran.
- Mencatat pihak "atas nama" bila instruksi dicatat sekretariat untuk pimpinan.
- Mendukung instruksi untuk individu atau beberapa unit.
- Menentukan kebutuhan bukti dan verifikasi.
- Menampilkan status dan penerima yang telah membaca.
- Menghasilkan tugas yang terhubung ke instruksi.
- Instruksi hanya dapat diubah selama berstatus draf. Setelah diterbitkan, perubahan dilakukan melalui pembatalan beralasan atau perubahan PIC/tenggat pada tugas terkait, dan semuanya tercatat di audit trail.

### 6.4 E-Task Management
- Membuat tugas dari disposisi, instruksi, keputusan rapat, atau penugasan langsung. Tindak lanjut (E-Follow Up) adalah tampilan atas tugas yang bersumber dari keputusan rapat, bukan sumber tugas terpisah.
- Menyimpan judul, deskripsi, sumber, unit, PIC, kolaborator, prioritas, tanggal mulai, tenggat, dan kriteria selesai.
- Mendukung subtask jika diperlukan.
- Mencatat progres, komentar, hambatan, serta perubahan PIC/tenggat.
- Menyediakan tampilan daftar, filter, pencarian, kalender, atau kanban.
- Menghindari duplikasi tugas dari sumber yang sama (satu tugas per disposisi, satu tugas per kombinasi instruksi–unit–PIC).

### 6.5 E-Monitoring
- Menampilkan progres, status, PIC, tenggat, umur tugas, dan sumber pekerjaan.
- Memfilter menurut unit, PIC, prioritas, tanggal, dan status.
- Menampilkan tugas belum dimulai, berjalan, terhambat, terlambat, menunggu verifikasi, perlu perbaikan, dan selesai.
- Mencatat hambatan serta keputusan yang dibutuhkan.
- Menyediakan riwayat pembaruan dan memungkinkan pejabat meminta pembaruan.
- Memisahkan progres yang dilaporkan dari keputusan akhir penyelesaian.

### 6.6 E-Reminder
- Mengirim notifikasi saat tugas/instruksi diterbitkan.
- Mengirim pengingat H-2 sebelum tenggat; opsi H-1 dan setelah tenggat dapat dikonfigurasi. H-n dihitung dalam hari kalender menurut zona waktu rumah sakit kecuali diputuskan lain (lihat Bab 16).
- Bila tenggat diubah, pengingat dijadwalkan ulang berdasarkan tenggat baru.
- Mengeskalasi keterlambatan kepada atasan sesuai aturan rumah sakit.
- Tidak mengirim pengingat berulang untuk tugas yang selesai atau dibatalkan.
- Mencatat penerima, kanal, waktu, status pengiriman, dan kegagalan.
- Mendukung notifikasi internal; email/WhatsApp dapat ditambahkan setelah disetujui dan dikonfigurasi.
- Tidak membocorkan isi dokumen rahasia melalui pesan singkat.

### 6.7 E-Agenda
- Membuat agenda dengan judul, jenis, tanggal, waktu, lokasi/tautan, penyelenggara, peserta, dan catatan.
- Mendukung undangan, perubahan jadwal, dan pembatalan.
- Menampilkan kalender dan daftar agenda.
- Menghubungkan rapat ke notulen dan keputusan.
- Mengirim pengingat sebelum kegiatan.
- Mengelola bahan rapat sesuai hak akses.

### 6.8 E-Notulen & Keputusan
- Menghubungkan notulen dengan agenda.
- Mencatat peserta, pokok pembahasan, ringkasan, dan keputusan.
- Menyimpan keputusan sebagai butir terstruktur.
- Menentukan PIC/unit, tenggat, prioritas, dan kriteria selesai untuk keputusan yang perlu tindakan.
- Membuat tindak lanjut melalui E-Follow Up/E-Task Management.
- Mendukung lampiran notulen dan riwayat revisi/persetujuan.

### 6.9 E-Follow Up
- Menampilkan tindak lanjut berdasarkan sumber.
- Menghubungkan tindak lanjut ke keputusan atau tugas asal.
- Menyimpan PIC, tenggat, status, progres, bukti, dan catatan.
- Menyediakan daftar tindak lanjut belum selesai untuk rapat evaluasi.
- Mendukung permintaan revisi/klarifikasi.
- Menghindari pencatatan tugas yang sama secara terpisah; tindak lanjut memakai entitas Task yang sama.
- Menghasilkan ringkasan tindak lanjut per rapat, unit, dan periode.

### 6.10 E-Arsip
- Menyimpan atau merujuk surat, disposisi, instruksi, agenda, notulen, laporan, dan bukti.
- Menyediakan metadata jenis, nomor, tanggal, pemilik, unit, klasifikasi, dan kata kunci.
- Mendukung versi dokumen bila ada revisi.
- Membatasi akses dan mencatat aktivitas penting.
- Menyediakan pencarian dan filter.
- Menetapkan retensi serta pemusnahan arsip sesuai kebijakan rumah sakit.
- Melindungi dokumen resmi dari penghapusan tanpa kewenangan.

### 6.11 E-Reporting
- Menyediakan laporan instruksi, disposisi, tugas, dan tindak lanjut menurut periode/unit/status.
- Menampilkan tugas selesai, terlambat, terhambat, dan menunggu verifikasi.
- Menghitung waktu penyelesaian dan persentase selesai tepat waktu.
- Mendukung filter periode, unit, PIC, jenis pekerjaan, dan status.
- Mendukung ekspor PDF/Excel jika diperlukan.
- Menampilkan waktu pembuatan laporan dan parameter filter.
- Membedakan pekerjaan yang belum diverifikasi dari yang sudah ditutup.

### 6.12 Executive Dashboard
- Menampilkan instruksi aktif dan belum dibaca.
- Menampilkan disposisi yang menunggu tindak lanjut.
- Menampilkan tugas belum dimulai, berjalan, H-2, terlambat, terhambat, menunggu verifikasi, dan selesai.
- Menampilkan agenda hari ini dan agenda mendatang (setelah E-Agenda tersedia pada Tahap 2).
- Menampilkan tindak lanjut keputusan rapat (setelah E-Notulen tersedia pada Tahap 2).
- Menampilkan kinerja unit dan tren penyelesaian.
- Menampilkan aktivitas terbaru yang relevan.
- Setiap angka dapat dibuka ke daftar detail dengan filter yang sesuai.

## 7. Alur Bisnis Utama

### 7.1 Surat masuk
1. Petugas mencatat surat dan mengunggah lampiran.
2. Surat diteruskan kepada pejabat berwenang.
3. Pejabat membuat disposisi, penerima, arahan, dan tenggat.
4. Penerima membaca dan menindaklanjuti.
5. Jika memerlukan pekerjaan, disposisi menghasilkan tugas tertaut.
6. PIC memperbarui progres dan bukti.
7. Pejabat memverifikasi jika diwajibkan.
8. Surat, disposisi, tugas, dan bukti saling tertaut di arsip.

### 7.2 Instruksi Direktur
1. Direktur atau sekretariat berwenang mencatat instruksi.
2. Penerima, PIC, prioritas, tenggat, dan kriteria selesai ditetapkan.
3. Sistem membuat tugas terkait.
4. PIC menerima notifikasi dan memperbarui progres.
5. Sistem mengirim pengingat sesuai aturan.
6. Keterlambatan ditandai dan dieskalasi sesuai kebijakan.
7. PIC mengirim hasil dan bukti.
8. Pejabat berwenang memverifikasi, meminta perbaikan, atau menutup pekerjaan.
9. Riwayat dan bukti disimpan.

### 7.3 Rapat dan keputusan
1. Agenda dibuat dan peserta diundang.
2. Notulen mencatat pembahasan dan keputusan.
3. Keputusan yang memerlukan tindakan dibuat menjadi tindak lanjut/tugas.
4. PIC dan tenggat ditetapkan.
5. Monitoring dan reminder memantau pelaksanaan.
6. Tindak lanjut dibahas kembali bila diperlukan.
7. Notulen, keputusan, dan bukti diarsipkan.

## 8. Status dan Aturan Bisnis

### Status tugas
Status berikut disimpan pada tugas. *Terlambat* dan *mendekati tenggat (H-2)* bukan status, melainkan penanda yang dihitung dari tenggat sehingga tetap berlaku bersamaan dengan status mana pun yang belum ditutup.

- Draf.
- Menunggu penerimaan.
- Belum dimulai.
- Berjalan.
- Terhambat.
- Menunggu verifikasi.
- Perlu perbaikan.
- Selesai.
- Dibatalkan.

Transisi yang diizinkan:

| Dari | Ke |
|---|---|
| Draf | Menunggu penerimaan, Dibatalkan |
| Menunggu penerimaan | Belum dimulai (diterima PIC), Dibatalkan |
| Belum dimulai | Berjalan, Terhambat, Dibatalkan |
| Berjalan | Terhambat, Menunggu verifikasi, Selesai (bila verifikasi tidak wajib), Dibatalkan |
| Terhambat | Berjalan, Dibatalkan |
| Menunggu verifikasi | Selesai, Perlu perbaikan, Dibatalkan |
| Perlu perbaikan | Berjalan, Terhambat, Menunggu verifikasi, Dibatalkan |
| Selesai, Dibatalkan | — (final) |

### Aturan bisnis
- Tugas resmi harus memiliki judul, sumber/alasan, PIC atau unit, dan status.
- Tugas yang memiliki tenggat harus memiliki tanggal tenggat.
- Perubahan PIC/tenggat setelah penugasan mencatat pengguna, waktu, dan alasan.
- Tugas lewat tenggat dihitung terlambat kecuali sudah selesai atau dibatalkan.
- Status *Terhambat* wajib disertai uraian hambatan; pembatalan dan pengembalian untuk perbaikan wajib disertai alasan.
- Tugas yang mewajibkan bukti tidak dapat dikirim untuk verifikasi sebelum minimal satu bukti diunggah.
- Progres 100% tidak otomatis berarti selesai; verifikasi mengikuti jenis tugas dan kewenangan.
- Instruksi/dokumen yang telah diterbitkan tidak boleh diubah diam-diam.
- Tugas dari modul lain tetap menyimpan tautan ke sumber.
- Tugas dan dokumen rahasia hanya dapat diakses pihak berwenang.

## 9. Notifikasi dan Eskalasi

| Pemicu | Penerima | Tindakan |
|---|---|---|
| Tugas/instruksi diterbitkan | PIC/penerima | Notifikasi penugasan |
| Belum dibaca setelah interval tertentu | Penerima | Pengingat |
| H-2 tenggat | PIC | Pengingat tenggat |
| H-1 tenggat | PIC | Pengingat tambahan bila belum selesai |
| Tenggat terlewati | PIC dan pihak terkait | Tandai terlambat dan beri notifikasi |
| Terlambat melewati ambang eskalasi | Atasan sesuai konfigurasi | Eskalasi |
| Bukti dikirim | Verifikator | Permintaan verifikasi |
| Hasil dikembalikan | PIC | Notifikasi perbaikan |
| Tugas ditutup | Pihak terkait | Notifikasi penyelesaian |

Jadwal dapat dikonfigurasi. Pengiriman harus tahan terhadap retry, mencatat kegagalan, dan tidak membuat notifikasi duplikat berlebihan. Zona waktu harus mengikuti pengaturan rumah sakit.

## 10. Kebutuhan Nonfungsional

### Keamanan
- Autentikasi dan manajemen sesi yang aman.
- Kontrol akses berdasarkan peran, unit, kepemilikan, dan klasifikasi.
- Proteksi CSRF, validasi input, dan pengamanan unggahan.
- HTTPS untuk produksi.
- Kredensial tidak disimpan hard-coded.
- Audit trail untuk aktivitas penting.
- Pembatasan dan pencatatan akses dokumen sensitif sesuai kebijakan.

### Kinerja dan keandalan
- Pagination dan filter server-side.
- Indeks database dan query dashboard yang terukur.
- Notifikasi dijalankan secara asynchronous.
- Backup database dan dokumen terjadwal serta uji pemulihan.
- Logging, pemantauan error, dan prosedur pemulihan.

### Kemudahan penggunaan
- Responsif untuk desktop dan ponsel.
- Navigasi dan status konsisten.
- Formulir memiliki validasi yang jelas.
- Aksi penting membutuhkan konfirmasi yang sesuai.

### Auditabilitas
- Mencatat perubahan status, PIC, tenggat, prioritas, verifikasi, dan aktivitas penting.
- Log memuat pengguna, waktu, aksi, objek, dan ringkasan perubahan.
- Log terlindungi dari perubahan pengguna biasa.
- Retensi log ditetapkan oleh pengelola sistem dan rumah sakit.

## 11. Model Data Konseptual

Entitas inti:
- User (peran, unit, atasan langsung), OrganizationUnit (hierarki induk–anak, kepala unit).
- IncomingLetter, OutgoingLetter.
- Disposition (dengan tautan penerusan), Instruction, InstructionTarget (penerima, PIC, waktu dibaca).
- Task, TaskAssignment, TaskUpdate.
- TaskEvidence, TaskVerification.
- ReminderLog, Notification, AuditLog.
- AgendaEvent, MeetingMinutes, MeetingDecision, FollowUp.
- DocumentArchive.

Relasi penting:
- Satu surat dapat memiliki beberapa disposisi.
- Satu instruksi dapat memiliki beberapa penerima; setiap penerima (unit + PIC) menghasilkan satu tugas.
- Satu rapat memiliki notulen dan dapat memiliki banyak keputusan.
- Satu keputusan dapat menghasilkan beberapa tindak lanjut.
- Setiap tugas menyimpan sumbernya: disposisi, instruksi, keputusan rapat, atau penugasan langsung.
- Bukti dan verifikasi terhubung ke tugas.
- Arsip menautkan dokumen ke objek bisnis terkait.

Kardinalitas, indeks, aturan penghapusan, dan skema fisik ditetapkan pada tahap ERD.

## 12. Arsitektur Teknis yang Disarankan

- Backend: Django 5.2 LTS, Python 3.12.
- Database: MySQL/MariaDB (diuji pada MariaDB 10.11). Catatan: MariaDB tidak mendukung unique constraint bersyarat (partial index), sehingga aturan anti-duplikasi memakai unique constraint biasa yang memanfaatkan sifat NULL pada unique index.
- Frontend: Bootstrap, Bootstrap Icons, dan HTMX yang disajikan dari aset statis lokal (tanpa CDN), dengan tema **Emboss Blue Glass (Kaca Biru Timbul)**: latar biru pucat, panel kaca putih timbul, isian cekung, tombol timbul, sidebar navy, aksen biru laut; area kertas tetap putih, sehingga aplikasi tetap berfungsi di jaringan internal tanpa akses internet dan tidak bergantung pada pihak ketiga.
- Background jobs: Celery dan Redis untuk reminder dan eskalasi. Celery wajib memakai DB Redis dan nama antrean khusus E-Office agar tidak mengonsumsi task aplikasi lain pada server yang sama.
- Dokumen: penyimpanan file terproteksi dengan metadata di database.
- Deployment: Dockerfile + Docker Compose, aplikasi di port **8090**, Nginx sebagai reverse proxy/TLS (lihat Bab 12.1).
- Laporan: PDF/Excel sesuai kebutuhan.
- Notifikasi: mulai dari notifikasi internal, kemudian email/WhatsApp bila disetujui.

Prinsip implementasi:
- Satu model Task menjadi pusat monitoring lintas modul.
- Logika modul dipisahkan dari layanan bersama seperti notifikasi, audit, dan arsip.
- Perubahan yang saling terkait memakai transaksi database.
- Background job harus idempotent agar retry tidak membuat duplikasi.
- Gunakan migrasi dan pengujian otomatis.
- Lingkungan pengembangan Python/Django wajib menggunakan virtual environment (`venv`). Instalasi paket Python dilakukan di dalam `venv`, bukan ke Python sistem.
- Standar implementasi, AI coding agent, skill, dan pengujian wajib mengikuti Bab 18.

### 12.1 Spesifikasi Docker dan Deployment

| Komponen | Ketentuan |
|---|---|
| `Dockerfile` | Base `python:3.12-slim`; dependensi dari `requirements.txt` yang dipatok; berjalan sebagai user non-root; `collectstatic` saat build; `HEALTHCHECK` ke `/healthz` |
| Port aplikasi | **8090** (Gunicorn `0.0.0.0:8090`, dapat diubah lewat variabel `PORT`) |
| Settings | `DJANGO_SETTINGS_MODULE=config.settings.prod`; `DEBUG=False`; `DJANGO_SECRET_KEY` wajib dari environment |
| `docker-compose.yml` | Layanan `web` (Gunicorn), `worker` (Celery, antrean `eoffice`), `beat` (jadwal pengingat harian) |
| Database & Redis | Menggunakan MariaDB/MySQL dan Redis yang sudah tersedia di host (`network_mode: host`, `DB_HOST=localhost`); kredensial hanya di `.env` yang tidak di-commit |
| Migrasi | Dijalankan oleh container `web` saat start bila `RUN_MIGRATIONS=1` |
| Penyimpanan berkas | Volume `eoffice_media` untuk lampiran dan bukti; tidak disajikan sebagai URL publik |
| HTTPS | Diterminasi di Nginx; aktifkan `DJANGO_SECURE_SSL_REDIRECT` dan `DJANGO_SECURE_COOKIES` setelah TLS siap |

Perintah standar:

```bash
docker compose up -d --build
docker compose exec web python manage.py createsuperuser
curl http://localhost:8090/healthz
```

## 13. MVP dan Kriteria Penerimaan

### Cakupan MVP
1. Pengguna, peran, unit, dan hak akses.
2. E-Surat dasar.
3. E-Disposisi.
4. E-Instruksi.
5. E-Task Management.
6. E-Monitoring.
7. E-Reminder H-2 dan status terlambat.
8. Executive Dashboard dasar.
9. Audit trail aktivitas inti.

E-Agenda, E-Notulen & Keputusan, E-Follow Up, E-Arsip lanjutan, dan E-Reporting dikembangkan pada tahap berikutnya, tetapi relasi datanya dipertimbangkan sejak awal.

### Kriteria penerimaan MVP
- Pengguna berwenang dapat membuat dan menerbitkan instruksi.
- Instruksi dapat memiliki PIC, unit, prioritas, dan tenggat.
- Tugas dari instruksi dan disposisi tampil dalam monitoring yang sama.
- PIC dapat menerima tugas, memperbarui progres, dan mengunggah bukti.
- Status terlambat dihitung berdasarkan tenggat.
- Reminder H-2 dijadwalkan/dikirim dan tercatat.
- Pejabat berwenang dapat memverifikasi atau meminta perbaikan.
- Angka dashboard dapat ditelusuri ke daftar detail.
- Pengguna tanpa izin tidak dapat membuka dokumen terbatas.
- Aktivitas penting tercatat pada audit trail.
- Backup dan pemulihan diuji sebelum produksi.

## 14. Tahapan Rilis

### Tahap 0 — Validasi
- Wawancara Direktur, sekretariat, kepala unit, staf, dan petugas arsip.
- Petakan alur surat, disposisi, instruksi, persetujuan, dan tindak lanjut.
- Tetapkan organisasi, hak akses, klasifikasi dokumen, dan kebijakan tenggat.

### Tahap 1 — Kontrol pekerjaan
- Pengguna, role/permission, unit kerja.
- E-Surat, E-Disposisi, E-Instruksi.
- E-Task Management, E-Monitoring, E-Reminder.
- Bukti pelaksanaan dan verifikasi tugas (diperlukan oleh kriteria penerimaan MVP).
- Executive Dashboard dasar dan audit trail.
- Dockerfile/Docker Compose pada port 8090.

### Tahap 2 — Rapat dan arsip
- E-Agenda.
- E-Notulen & Keputusan.
- E-Follow Up.
- E-Arsip (metadata, versi, retensi), termasuk pengarsipan bukti pelaksanaan dari Tahap 1.

### Tahap 3 — Pelaporan dan integrasi
- E-Reporting lanjutan.
- Ekspor laporan.
- Integrasi notifikasi eksternal jika disetujui.
- Evaluasi dan penyempurnaan berdasarkan penggunaan.

## 15. Risiko dan Mitigasi

| Risiko | Dampak | Mitigasi |
|---|---|---|
| Proses bisnis belum disepakati | Fitur tidak sesuai kebutuhan | Validasi workflow sebelum coding |
| PIC/tenggat kosong | Monitoring tidak efektif | Validasi field sesuai jenis pekerjaan |
| Notifikasi terlalu banyak | Pengguna mengabaikan pengingat | Frekuensi dan eskalasi bertahap |
| Status tidak konsisten | Dashboard tidak akurat | Satu mesin status tugas bersama |
| Dokumen rahasia terbuka | Risiko kerahasiaan | Kontrol akses dan pengujian izin |
| Bukti tidak memadai | Penyelesaian sulit diverifikasi | Kriteria selesai dan bukti wajib sesuai kategori |
| Arsip sulit dicari | Waktu pencarian meningkat | Standar metadata dan indeks |
| Backup tidak bisa dipulihkan | Kehilangan data | Uji pemulihan berkala |

## 16. Keputusan yang Harus Divalidasi

1. Apakah hanya Direktur atau juga Wakil Direktur yang dapat menerbitkan instruksi?
2. Apakah sekretariat boleh membuat instruksi atas nama Direktur, dan bagaimana persetujuannya?
3. Apakah setiap instruksi wajib memiliki tenggat? (Implementasi awal: disposisi yang memerlukan tindakan dan penugasan langsung wajib bertenggat; tenggat instruksi opsional.)
4. Siapa yang memverifikasi pekerjaan selesai?
5. Berapa lama keterlambatan sebelum eskalasi ke atasan? (Implementasi awal: 3 hari, dapat dikonfigurasi.)
6. Apakah tugas dapat memiliki beberapa PIC, dan siapa PIC utama?
7. Apakah disposisi boleh diteruskan?
8. Kanal notifikasi yang diizinkan: aplikasi, email, WhatsApp, atau kombinasi?
9. Apakah tanda tangan elektronik diperlukan pada tahap pertama?
10. Bagaimana klasifikasi, retensi, dan pemusnahan arsip?
11. Apa format nomor surat, agenda, dan instruksi?
12. Laporan apa yang wajib tersedia untuk rapat direksi dan evaluasi unit?
13. Apakah H-2 dihitung dalam hari kalender atau hari kerja (dengan kalender libur rumah sakit)?

## 17. Rekomendasi Akhir

Bangun E-Office sebagai satu sistem terintegrasi, bukan 12 aplikasi terpisah. Pusat desain teknisnya adalah **E-Task Management + E-Monitoring + E-Reminder**, sedangkan E-Surat, E-Disposisi, E-Instruksi, dan E-Notulen menjadi sumber pekerjaan yang saling tertaut.

Setelah proses bisnis divalidasi, turunkan PRD ini menjadi:
1. Diagram workflow.
2. ERD dan desain database.
3. Matriks hak akses.
4. Wireframe setiap halaman.
5. Backlog user story dan prioritas MVP.
6. Rencana pengujian dan deployment.

Dokumen ini adalah spesifikasi kebutuhan awal dan bukan pengganti kebijakan resmi, SOP rumah sakit, atau tinjauan keamanan sebelum digunakan dalam produksi.


## 18. Standar Implementasi, AI Coding Agent, dan Quality Assurance

Bab ini merupakan persyaratan implementasi yang wajib dipatuhi oleh pengembang manusia maupun AI coding agent (misalnya Claude Code, Codex, atau agent lain). Persyaratan ini melengkapi kebutuhan fungsional pada bab sebelumnya.

### 18.1 Standar Django dan Python

1. Backend wajib menggunakan Django dengan struktur aplikasi yang modular berdasarkan domain bisnis. Nama dan pembagian aplikasi final ditetapkan setelah desain teknis, tetapi pemisahan tanggung jawab harus jelas.
2. Pengembangan lokal wajib memakai Python virtual environment (`venv`). Jangan memasang dependensi proyek ke Python sistem.
3. Dokumentasi proyek harus menyediakan perintah yang konsisten untuk membuat dan mengaktifkan `venv`, memasang dependensi, menjalankan migrasi, membuat akun administrator, menjalankan server pengembangan, dan menjalankan pengujian.
4. Dependensi wajib dicatat dalam berkas yang sesuai dengan strategi proyek, misalnya `requirements.txt` dengan versi yang dipatok atau mekanisme lockfile yang disepakati.
5. Rahasia seperti `SECRET_KEY`, kredensial database, token, dan kunci integrasi harus berasal dari environment variables atau secret store; jangan memasukkannya ke repository.
6. Konfigurasi development, testing, dan production harus dipisahkan. Konfigurasi produksi tidak boleh bergantung pada `DEBUG=True`.
7. Model, validasi, business logic, akses database, dan tampilan harus dipisahkan secara wajar. Hindari menempatkan seluruh business logic di view atau template.
8. Gunakan Django ORM dan migrasi resmi untuk perubahan skema. Perubahan database manual yang tidak tercermin dalam migrasi tidak diperbolehkan untuk skema aplikasi.
9. Perubahan model harus disertai migrasi yang diperiksa. Migrasi tidak boleh menghapus atau mengubah data penting secara destruktif tanpa rencana migrasi, backup, dan persetujuan.
10. Akses lintas unit, kepemilikan tugas, dan klasifikasi dokumen harus diperiksa di sisi server; menyembunyikan tombol di antarmuka saja tidak dianggap sebagai kontrol keamanan.
11. Gunakan transaksi database untuk operasi yang mengubah beberapa objek yang harus konsisten. Background job harus idempotent atau memiliki perlindungan duplikasi yang memadai.
12. Docker digunakan untuk lingkungan integrasi dan produksi sesuai Bab 12.1 (port 8090). Penggunaan Docker tidak menghapus kewajiban penggunaan `venv` pada lingkungan pengembangan lokal. Image produksi harus menggunakan dependensi yang tercatat dan konfigurasi yang aman.
13. Perintah dan panduan Python/Django dalam dokumentasi harus menunjukkan penggunaan `venv`, kecuali secara eksplisit menjelaskan lingkungan container.
14. Sebelum mengubah struktur proyek yang sudah ada, agent wajib memeriksa struktur direktori, `settings`, `urls`, model, migrasi, pola autentikasi, test suite, dan konvensi yang telah digunakan. Jangan mengganti arsitektur yang berjalan tanpa alasan dan rencana migrasi.

### 18.2 Standar AI Coding Agent

AI coding agent harus bekerja berdasarkan repository dan dokumentasi aktual, bukan mengarang struktur file atau menganggap implementasi sudah ada.

Sebelum coding, agent wajib:
1. Memeriksa struktur repository dan membaca dokumentasi proyek yang relevan.
2. Memeriksa status Git, branch aktif, dan perubahan lokal. Jangan menimpa perubahan pengguna yang belum disimpan.
3. Memeriksa skill yang tersedia dan membaca skill yang relevan sebelum mulai mengerjakan tugas.
4. Menyusun ringkasan pemahaman, file yang kemungkinan terdampak, aturan bisnis terkait, serta rencana pengujian.
5. Mengidentifikasi dependensi terhadap modul bersama seperti task, notifikasi, audit trail, arsip, dan hak akses.

Selama coding, agent wajib:
1. Mengikuti pola arsitektur dan konvensi repository yang sudah disepakati.
2. Membuat perubahan sekecil dan sejelas mungkin serta menghindari refactor tidak terkait.
3. Tidak menghapus validasi, permission check, audit logging, atau pengujian hanya agar implementasi terlihat berhasil.
4. Tidak menandai pekerjaan selesai apabila pengujian yang relevan belum dijalankan atau kegagalannya belum dijelaskan.
5. Tidak mengklaim telah menjalankan perintah, test, atau migrasi apabila memang belum dijalankan.
6. Menyampaikan perubahan skema database, migrasi, konfigurasi environment, dan langkah deployment yang dibutuhkan.
7. Menyertakan ringkasan perubahan, daftar file penting, hasil pengujian, risiko yang tersisa, dan langkah verifikasi manual.

### 18.3 Kebijakan Pembuatan dan Pemeliharaan Skill

Skill adalah instruksi kerja reusable untuk membantu AI coding agent mengerjakan tugas secara konsisten. Skill tidak menggantikan dokumentasi arsitektur, pengujian, code review, atau keputusan manusia.

Agent wajib:
- Memeriksa apakah skill yang relevan sudah tersedia sebelum membuat skill baru.
- Menggunakan dan mengikuti skill yang sudah ada bila masih sesuai.
- Mengusulkan pembuatan atau pembaruan skill jika pekerjaan berulang, aturan khusus proyek belum terdokumentasi, atau pola implementasi baru perlu distandardisasi.
- Menghindari duplikasi skill dengan tujuan yang sama.
- Menyertakan contoh yang sesuai dengan repository dan menjaga agar instruksi skill tidak bertentangan dengan PRD, kebijakan keamanan, atau arsitektur aktual.
- Meminta persetujuan pengguna bila pembuatan atau perubahan skill akan mengubah workflow tim secara signifikan.

Skill minimum yang direkomendasikan untuk proyek ini:

| Nama skill yang disarankan | Cakupan |
|---|---|
| `django-project-standards` | Struktur Django, penggunaan `venv`, konfigurasi, coding conventions, dan dokumentasi |
| `eoffice-module-development` | Pola pengembangan modul E-Office dan integrasi antarmodul |
| `django-model-migration` | Model, migrasi, integritas data, transaksi, dan prosedur perubahan skema |
| `django-permission-security` | Role, permission, akses per unit, klasifikasi dokumen, dan pengujian akses |
| `eoffice-workflow` | Aturan disposisi, instruksi, task, verifikasi, reminder, dan audit trail |
| `eoffice-e2e-testing` | Strategi pengujian end-to-end dan skenario alur utama E-Office |
| `emboss-blue-glass-theme` | Tema UI Emboss Blue Glass, kontrak markup shell (sidebar/topbar), area kertas, halaman login |

Lokasi dan format skill mengikuti alat agent yang digunakan. Sebagai contoh, skill dapat disimpan pada direktori konfigurasi agent yang dipakai repository. Lokasi final harus ditulis dalam dokumentasi proyek dan tidak boleh diasumsikan sama untuk semua agent.

### 18.4 Strategi Pengujian Wajib

Pengujian harus berlapis. Pilihan library dapat disesuaikan dengan repository, tetapi cakupan di bawah wajib dipenuhi.

#### A. Unit test
Menguji fungsi dan aturan bisnis secara terisolasi, termasuk:
- Perhitungan status terlambat dan sisa waktu tenggat.
- Validasi PIC, tenggat, prioritas, dan kriteria penyelesaian.
- Transisi status tugas yang diperbolehkan.
- Aturan progres 100% yang tidak otomatis menutup tugas.
- Pembentukan tugas dari sumber disposisi, instruksi, atau keputusan rapat.
- Aturan reminder, eskalasi, dan pencegahan notifikasi duplikat.

#### B. Integration test
Menguji interaksi komponen, termasuk:
- View/API dengan database dan permission.
- Pembuatan tugas dari modul sumber dan tautan balik ke sumber tersebut.
- Pengunggahan serta akses bukti/dokumen.
- Pemrosesan background job dan pencatatan hasil pengiriman notifikasi.
- Dashboard dan laporan dengan data tugas yang benar.
- Transaksi dan perilaku ketika proses gagal di tengah jalan.

#### C. Browser end-to-end (E2E) test
Pengujian E2E wajib menguji alur pengguna melalui browser pada lingkungan testing. Playwright direkomendasikan; pilihan alat lain dapat digunakan jika sudah distandardisasi dan dapat menjalankan skenario browser yang sama.

Skenario E2E minimum:
1. **Instruksi sampai penutupan:** pengguna berwenang membuat instruksi, menetapkan unit/PIC/tenggat, menerbitkan instruksi, PIC melihat tugas, memperbarui progres, mengunggah bukti, mengirim untuk verifikasi, verifikator menyetujui, dan dashboard mencerminkan status akhir.
2. **Surat dan disposisi:** petugas mencatat surat masuk, pejabat membuat disposisi, penerima menindaklanjuti, dan tugas yang dihasilkan terhubung dengan surat/disposisi asal.
3. **Keputusan rapat:** keputusan yang memerlukan tindakan menghasilkan tindak lanjut/tugas tanpa duplikasi. *(Wajib sejak modul E-Notulen tersedia pada Tahap 2.)*
4. **Reminder H-2:** gunakan tanggal/waktu yang dikendalikan atau clock mocking pada lingkungan testing; verifikasi bahwa reminder dibuat, penerima benar, log tercatat, dan pengulangan job tidak membuat duplikasi.
5. **Terlambat dan eskalasi:** tugas yang melewati tenggat ditandai terlambat dan eskalasi mengikuti konfigurasi.
6. **Perlu perbaikan:** verifikator mengembalikan bukti dengan alasan, PIC menerima notifikasi, melakukan perbaikan, lalu mengirim ulang.
7. **Permission dan kerahasiaan:** pengguna dari unit atau peran yang tidak berwenang tidak dapat melihat, mengunduh, mengubah, atau menebak URL dokumen/tugas terbatas.
8. **Audit trail:** perubahan PIC, tenggat, status, dan verifikasi menghasilkan catatan audit yang dapat ditelusuri.
9. **Filter dashboard:** membuka angka ringkasan membawa pengguna ke daftar detail yang konsisten dengan filter dan hak aksesnya.
10. **Kegagalan notifikasi:** kegagalan pengiriman tercatat dan mekanisme retry tidak membuat pengiriman/record duplikat yang tidak diinginkan.

E2E tidak boleh menggunakan data pasien atau data pribadi nyata. Gunakan data sintetis dan akun testing khusus.

### 18.5 Data dan Lingkungan Testing

- Sediakan konfigurasi testing terpisah dari database development dan production.
- Pengujian otomatis tidak boleh berjalan terhadap database produksi.
- Gunakan factory/fixture atau mekanisme sejenis untuk data sintetis yang konsisten.
- Uji background job menggunakan mode eager/mock atau worker khusus testing sesuai kebutuhan, dan tetap lakukan setidaknya satu uji integrasi yang memvalidasi konfigurasi job.
- Waktu, tanggal, dan zona waktu harus dapat dikendalikan pada test reminder dan tenggat.
- File bukti testing harus menggunakan file dummy yang aman.
- Dokumentasikan cara menjalankan seluruh test suite dan subset test yang relevan.
- CI direkomendasikan menjalankan lint/static checks bila tersedia, unit test, integration test, dan E2E yang ditetapkan untuk pipeline. E2E yang memerlukan layanan tambahan harus menyiapkan dependensinya secara eksplisit.

### 18.6 Quality Gate dan Definition of Done

Sebuah fitur tidak boleh dinyatakan selesai sebelum seluruh kriteria yang relevan dipenuhi:

- [ ] Kebutuhan dan aturan bisnis sudah jelas atau asumsi dicatat untuk validasi.
- [ ] Implementasi mengikuti struktur dan konvensi Django proyek.
- [ ] Pengembangan lokal menggunakan `venv` dan dependensi diperbarui dengan benar.
- [ ] Permission diperiksa di sisi server dan diuji untuk akses yang diizinkan maupun ditolak.
- [ ] Migrasi dibuat dan diperiksa jika skema berubah.
- [ ] Unit test untuk aturan bisnis baru/berubah tersedia dan lulus.
- [ ] Integration test untuk interaksi yang terdampak tersedia dan lulus.
- [ ] E2E test ditambahkan atau diperbarui untuk alur pengguna kritis yang terdampak.
- [ ] Tidak ada regresi pada alur utama yang telah ditetapkan.
- [ ] Audit trail, notifikasi, dan penanganan error diterapkan bila relevan.
- [ ] Dokumentasi pengguna/pengembang, konfigurasi, dan skill terkait diperbarui bila diperlukan.
- [ ] Hasil pengujian dilaporkan secara jujur, termasuk test yang belum dapat dijalankan.
- [ ] Risiko yang tersisa dan langkah deployment/migrasi dijelaskan.

Untuk perubahan kritis yang menyangkut hak akses, kerahasiaan, transisi status, atau data resmi, code review manusia wajib dilakukan sebelum rilis produksi.

### 18.7 Dokumentasi Repository Minimum

Repository wajib memelihara dokumentasi yang relevan, setidaknya:
- `README.md`: gambaran proyek dan cara menjalankan proyek.
- `.env.example`: daftar variabel konfigurasi tanpa rahasia.
- Panduan setup `venv`, instalasi dependensi, migrasi, test, dan server development.
- Ringkasan arsitektur dan batas tanggung jawab modul.
- Dokumentasi aturan workflow dan status tugas.
- Panduan backup, restore, deployment, dan rollback migrasi.
- Panduan menjalankan unit, integration, dan E2E tests.
- Daftar skill agent yang tersedia, lokasi, cakupan, dan aturan pemeliharaannya.

Nama berkas dapat disesuaikan dengan repository, tetapi informasi tersebut harus tersedia dan mudah ditemukan.

### 18.8 Persyaratan Keamanan dan Audit untuk Pengujian

- Setiap skenario izin harus menguji akses yang sah dan akses yang ditolak.
- Pemeriksaan akses harus dilakukan pada setiap endpoint yang mengembalikan atau mengubah data sensitif, termasuk unduhan file.
- Informasi rahasia tidak boleh bocor melalui pesan error, log aplikasi, notifikasi, atau URL publik.
- Uji audit trail untuk aksi kritis: penerbitan instruksi, perubahan PIC/tenggat, verifikasi, pembatalan, dan perubahan klasifikasi dokumen.
- Uji bahwa pengguna biasa tidak dapat mengubah atau menghapus audit trail.
- Pemeriksaan keamanan otomatis dapat ditambahkan, tetapi tidak menggantikan tinjauan konfigurasi dan permission secara manual.

## 19. Instruksi Implementasi untuk AI Coding Agent

Instruksi berikut dapat digunakan sebagai standar awal ketika agent diberi tugas mengembangkan E-Office:

> Anda bekerja pada proyek E-Office Terintegrasi untuk Direktur Rumah Sakit. Sebelum mengubah kode, periksa repository, dokumentasi, status Git, pola arsitektur, migrasi, permission, test suite, dan skill agent yang tersedia. Ikuti PRD ini serta aturan repository. Untuk pengembangan lokal Python/Django, gunakan `venv`. Jangan mengarang struktur file atau menganggap test telah lulus tanpa menjalankannya.
>
> Pecah pekerjaan menjadi perubahan kecil. Jaga keterkaitan antar modul dan gunakan satu sumber kebenaran untuk task, monitoring, reminder, dan audit trail. Terapkan permission di server, validasi data, transaksi bila diperlukan, dan migrasi Django untuk perubahan skema. Jangan menimpa perubahan lokal pengguna.
>
> Sebelum menyatakan pekerjaan selesai, jalankan unit test dan integration test yang relevan serta E2E untuk alur kritis yang terdampak. Jika suatu test tidak dapat dijalankan, jelaskan alasannya dan jangan mengklaim lulus. Periksa apakah skill yang relevan tersedia; usulkan pembaruan/pembuatan skill bila diperlukan dan hindari duplikasi. Laporkan ringkasan perubahan, file yang diubah, migrasi, perintah pengujian beserta hasilnya, risiko, dan langkah verifikasi.
>
> Fitur hanya dianggap selesai jika memenuhi Definition of Done pada Bab 18.6.

## 20. Tambahan Kriteria Penerimaan Proyek

Kriteria berikut melengkapi kriteria penerimaan MVP pada Bab 13:
- Proyek memiliki panduan setup dan menjalankan Django menggunakan `venv`.
- Perubahan skema menggunakan migrasi Django yang dapat ditinjau.
- Pengujian otomatis tersedia untuk aturan bisnis utama, permission, dan integrasi modul.
- Alur instruksi/disposisi hingga verifikasi dan dashboard memiliki E2E test yang dapat diulang.
- Reminder dan eskalasi dapat diuji tanpa menunggu tanggal nyata.
- Skill agent yang dipakai tercatat dalam dokumentasi repository; skill relevan diperiksa sebelum pekerjaan dilakukan.
- Laporan penyelesaian pekerjaan coding menyebutkan test yang dijalankan dan hasilnya.
- Pipeline CI (jika disiapkan) gagal bila quality gate wajib gagal.
- Sebelum produksi, dilakukan uji backup/restore, pemeriksaan konfigurasi keamanan, dan persetujuan pemilik proses bisnis.

## 21. Keputusan Teknis yang Perlu Dikonfirmasi

1. Versi Python dan Django yang akan distandardisasi. (Implementasi awal: Python 3.12, Django 5.2 LTS.)
2. Apakah test runner memakai Django Test Framework, `pytest-django`, atau kombinasi. (Implementasi awal: Django Test Framework.)
3. Apakah Playwright digunakan sebagai standar E2E dan browser apa yang wajib diuji.
4. Apakah pipeline CI akan menggunakan GitHub Actions, GitLab CI, atau sistem internal.
5. Di mana skill AI coding agent disimpan sesuai tool yang digunakan tim.
6. Apakah ada persyaratan code review wajib untuk seluruh perubahan atau hanya perubahan kritis.
7. Format dan retensi artefak hasil test, log audit, dan laporan CI.

## 22. Status Implementasi dan Riwayat Revisi

### Status implementasi MVP (30 Oktober 2026)

| Bagian | Status |
|---|---|
| Pengguna, peran, unit, hak akses server-side | Tersedia |
| E-Surat (masuk/keluar), E-Disposisi (termasuk penerusan) | Tersedia |
| E-Instruksi (draf, penerima, terbit, status baca, batal) | Tersedia |
| E-Task Management & E-Monitoring (mesin status, progres, hambatan, bukti, verifikasi, ubah PIC/tenggat) | Tersedia |
| E-Reminder (H-2, terlambat, eskalasi, idempotent, retry kegagalan) | Tersedia |
| Executive Dashboard dasar (angka tertaut ke daftar terfilter) | Tersedia |
| Audit trail append-only | Tersedia |
| Dockerfile & Docker Compose port 8090 | Tersedia |
| Tema UI Emboss Blue Glass (Kaca Biru Timbul) + halaman login seragam casemix | Tersedia |
| Skill AI coding agent (Bab 18.3) di `.claude/skills/` + tema | Tersedia (7 skill) |
| Unit & integration test | Tersedia |
| E2E browser (Playwright) | Belum; skenario 1, 2, 7, dan 9 baru diuji pada level HTTP |
| E-Agenda, E-Notulen, E-Follow Up, E-Arsip lanjutan, E-Reporting | Tahap 2–3 |

### Riwayat revisi

| Versi | Perubahan |
|---|---|
| 1.1 | Draft awal beserta standar implementasi dan QA. |
| 1.2 | Perbaikan redaksi Bab 2; penyelarasan sumber tugas (6.4, 6.9, 11); status disposisi; penegasan bahwa *terlambat*/H-2 adalah penanda terhitung, bukan status; tabel transisi status; aturan bukti wajib dan alasan wajib; bukti & verifikasi dipindah ke Tahap 1 agar konsisten dengan kriteria MVP; catatan Tahap 2 untuk dashboard agenda/notulen dan E2E keputusan rapat; aset frontend tanpa CDN; isolasi antrean Celery; spesifikasi Docker port 8090 (Bab 12.1); status implementasi. |
