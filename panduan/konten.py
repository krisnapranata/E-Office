"""Isi halaman Panduan. Ditulis sebagai DATA supaya:
- tautan memakai nama URL (divalidasi `reverse()` oleh test — tidak ada tautan mati);
- nilai yang dapat dikonfigurasi (H-n, ambang eskalasi, jam pengingat, jenis/ukuran berkas, peran penerbit
  instruksi) dibaca dari settings saat halaman dibuka, jadi panduan selalu sama dengan perilaku sistem.

Nama tombol/menu di sini HARUS sama persis dengan teks di templat. Bila mengubah alur/tombol, perbarui berkas ini.
Placeholder `{nama}` diisi oleh `panduan.views._konteks_aturan()`.
"""
from accounts.models import Role

# --------------------------------------------------------------------------- alur besar
ALUR = [
    ("bi-inbox", "1. Pekerjaan masuk",
     "Lewat empat pintu: <b>surat masuk → disposisi</b>, <b>instruksi Direktur</b>, <b>keputusan rapat</b> "
     "(agenda → notulen disetujui), atau <b>penugasan langsung</b> oleh atasan. Semuanya menjadi <b>tugas</b> dengan "
     "PIC, tenggat, dan pemeriksa (verifikator)."),
    ("bi-person-check", "2. PIC menerima",
     "PIC mendapat notifikasi <i>Tugas baru</i>, membuka tugas, lalu menekan <b>Terima tugas</b>."),
    ("bi-graph-up-arrow", "3. Dikerjakan & dilaporkan",
     "PIC melaporkan progres (%), menandai <b>Terhambat</b> bila ada kendala, dan mengunggah <b>bukti</b>."),
    ("bi-send-check", "4. Hasil dikirim",
     "PIC menekan <b>Kirim untuk verifikasi</b>. Progres 100% saja belum berarti selesai."),
    ("bi-patch-check", "5. Diverifikasi",
     "Pemeriksa memilih <b>Setujui &amp; tutup</b> atau <b>Kembalikan untuk perbaikan</b> (dengan alasan)."),
    ("bi-alarm", "6. Dipantau otomatis",
     "Setiap hari pukul {jam_pengingat}.00 sistem mengirim pengingat {hari_pengingat}, menandai tugas "
     "<b>terlambat</b>, dan <b>mengeskalasi</b> ke atasan bila terlambat ≥ {hari_eskalasi} hari."),
    ("bi-speedometer2", "7. Dashboard & laporan",
     "Pimpinan melihat ringkasan dan agenda; setiap angka dapat diklik. Laporan periodik dibuat di E-Reporting."),
    ("bi-archive", "8. Diarsipkan",
     "Lampiran surat, instruksi, bahan rapat, notulen, dan bukti tugas otomatis masuk <b>E-Arsip</b> beserta "
     "metadata dan masa retensinya."),
]

STATUS = [
    ("Menunggu penerimaan", "secondary", "Tugas sudah diterbitkan, PIC belum menekan <b>Terima tugas</b>."),
    ("Belum dimulai", "secondary", "PIC sudah menerima, belum ada laporan progres."),
    ("Berjalan", "primary", "PIC sedang mengerjakan dan melaporkan progres."),
    ("Terhambat", "warning", "Ada kendala. PIC wajib menulis hambatan; pimpinan bisa membaca "
                             "<i>keputusan yang dibutuhkan</i> di riwayat progres."),
    ("Menunggu verifikasi", "info", "Hasil &amp; bukti sudah dikirim, menunggu pemeriksa."),
    ("Perlu perbaikan", "warning", "Pemeriksa mengembalikan hasil dengan alasan. PIC memperbaiki lalu mengirim ulang."),
    ("Selesai", "success", "Disetujui pemeriksa (atau dikirim PIC bila verifikasi tidak wajib). Final."),
    ("Dibatalkan", "dark", "Dibatalkan dengan alasan oleh pemberi tugas/pimpinan. Final."),
]

PENANDA = [
    ("Terlambat", "danger", "Bukan status, melainkan penanda: tenggat sudah lewat dan tugas belum Selesai/Dibatalkan."),
    ("Tenggat ≤ H-2", "warning", "Penanda di dashboard: tenggat hari ini sampai 2 hari lagi."),
    ("Rahasia", "light", "Klasifikasi dokumen. Hanya pihak yang terlibat dan Direktur yang dapat melihat; "
                         "judulnya tidak ditampilkan di notifikasi."),
]

# --------------------------------------------------------------------------- tugas umum (dipakai beberapa peran)
# Setiap tugas: judul, url (nama URL atau None), dan langkah-langkah.
T_NOTIF = {
    "judul": "Membaca notifikasi",
    "url": "notifications:list",
    "langkah": [
        "Ikon lonceng di kanan atas menampilkan jumlah notifikasi yang belum dibaca (diperbarui tiap menit).",
        "Klik ikon <b>lonceng</b> di kanan atas, lalu tekan <b>Buka</b> pada notifikasi: notifikasi ditandai dibaca dan Anda "
        "langsung diarahkan ke tugas/instruksi/disposisi terkait.",
        "Tekan <b>Tandai semua dibaca</b> untuk membersihkan daftar.",
    ],
}
T_KERJAKAN = {
    "judul": "Mengerjakan tugas sebagai PIC",
    "url": "workflow:list",
    "langkah": [
        "Buka <b>Tugas</b>. Daftar hanya berisi tugas yang boleh Anda lihat. Pakai filter "
        "<b>Penanda: Terlambat</b> atau <b>Tenggat ≤ H-2</b> untuk memprioritaskan.",
        "Klik judul tugas. Baca <b>Sumber</b> (instruksi/disposisi asal dapat diklik), <b>Kriteria selesai</b>, "
        "dan tenggat.",
        "Tekan <b>Terima tugas</b>. Membuka tugas dari instruksi otomatis mencatat bahwa Anda telah membaca instruksinya.",
        "Di kartu <b>Laporkan progres</b>: isi progres (0–100%), pilih status <b>Berjalan</b> atau <b>Terhambat</b>, "
        "lalu <b>Simpan progres</b>. Bila Terhambat, kolom <b>Hambatan</b> wajib diisi; isi juga "
        "<b>Keputusan yang dibutuhkan</b> bila Anda menunggu keputusan pimpinan.",
        "Di kartu <b>Unggah bukti</b>: pilih berkas ({jenis_berkas}, maks. {ukuran_berkas} MB), beri keterangan, "
        "tekan <b>Unggah</b>. Bukti dapat diunggah berkali-kali.",
        "Setelah selesai, tekan <b>Kirim untuk verifikasi</b> (atau <b>Kirim &amp; selesai</b> bila verifikasi "
        "tidak wajib). Bila tugas wajib bukti, hasil tidak bisa dikirim sebelum ada minimal satu bukti.",
        "Setelah terkirim, laporan progres dikunci sampai pemeriksa memutuskan.",
    ],
}
T_PERBAIKAN = {
    "judul": "Bila hasil dikembalikan (Perlu perbaikan)",
    "url": None,
    "langkah": [
        "Anda menerima notifikasi <i>Perlu perbaikan</i>. Buka tugasnya.",
        "Baca alasan di kartu <b>Verifikasi</b> (mis. \"foto buram\").",
        "Perbaiki pekerjaan, unggah bukti baru, lalu tekan <b>Kirim untuk verifikasi</b> lagi.",
    ],
}
T_KOLABORATOR = {
    "judul": "Sebagai kolaborator",
    "url": None,
    "langkah": [
        "Kolaborator dapat melihat tugas, melaporkan progres, dan mengunggah bukti.",
        "Hanya PIC yang dapat <b>Terima tugas</b> dan <b>Kirim untuk verifikasi</b>.",
    ],
}
T_VERIFIKASI = {
    "judul": "Memverifikasi hasil",
    "url": "workflow:list",
    "langkah": [
        "Anda menerima notifikasi <i>Menunggu verifikasi</i>, atau buka <b>Tugas</b> dengan filter "
        "<b>Status: Menunggu verifikasi</b>.",
        "Buka tugas, periksa <b>Bukti pelaksanaan</b> (klik nama berkas untuk mengunduh) dan riwayat progres.",
        "Di kartu <b>Verifikasi hasil</b> pilih <b>Setujui &amp; tutup</b> atau <b>Kembalikan untuk perbaikan</b>. "
        "Pengembalian wajib disertai alasan; PIC langsung dinotifikasi.",
        "Pemeriksa sebuah tugas adalah pemberi tugas: penerbit instruksi (atau pihak \"atas nama\"), pemberi "
        "disposisi, atau atasan yang membuat penugasan langsung.",
        "Bila tugas berasal dari disposisi, status disposisinya otomatis menjadi <i>Selesai</i> saat tugas disetujui.",
    ],
}
T_KENDALI = {
    "judul": "Mengendalikan tugas (minta pembaruan, ubah PIC/tenggat, batalkan)",
    "url": "workflow:list",
    "langkah": [
        "Buka tugas. Kartu <b>Pengendalian</b> muncul bila Anda Direktur, pembuat tugas, pemeriksanya, atau atasan "
        "unit tugas tersebut (dan bukan PIC-nya).",
        "<b>Minta pembaruan ke PIC</b>: mengirim notifikasi ke PIC agar melaporkan progres.",
        "<b>Ubah PIC/tenggat</b>: pilih PIC baru dan/atau tenggat baru, isi <b>Alasan perubahan</b> (wajib). "
        "Perubahan tercatat di audit trail dan PIC baru dinotifikasi. Pengingat dijadwalkan ulang mengikuti tenggat baru.",
        "<b>Batalkan tugas</b>: isi alasan (wajib). Tugas yang sudah Selesai/Dibatalkan tidak dapat diubah lagi.",
    ],
}
T_LANGSUNG = {
    "judul": "Membuat penugasan langsung",
    "url": "workflow:create",
    "langkah": [
        "Buka <b>Tugas</b> → <b>+ Beri tugas baru</b> (atau tombol <b>Beri tugas</b> di Beranda).",
        "Isi judul, <b>Alasan/sumber lain</b> (wajib, mis. \"temuan ronde mutu\"), unit, <b>PIC</b>, kolaborator "
        "(opsional), prioritas, klasifikasi, tanggal mulai, <b>tenggat</b> (wajib), dan kriteria selesai.",
        "Centang <b>Wajib bukti</b> / <b>Wajib verifikasi</b> sesuai kebutuhan, lalu <b>Simpan &amp; terbitkan</b>.",
        "Anda otomatis menjadi pemeriksa tugas ini.",
    ],
}
T_INSTRUKSI = {
    "judul": "Membuat dan menerbitkan instruksi",
    "url": "instructions:create",
    "langkah": [
        "Buka <b>Instruksi</b> → <b>+ Instruksi baru</b>. Isi judul, uraian, tanggal, prioritas, klasifikasi, "
        "tenggat, kriteria selesai, lampiran (opsional), lalu <b>Simpan draf</b>. Kode (mis. INS/2026/0001) dibuat otomatis.",
        "Di halaman instruksi, kartu <b>Tambah penerima</b>: pilih unit dan PIC → <b>Tambah</b>. Ulangi untuk setiap "
        "penerima. Selama masih draf, isi dapat diubah lewat <b>Ubah draf</b> dan penerima dapat dihapus.",
        "Tekan <b>Terbitkan</b>. Sistem membuat <b>satu tugas untuk setiap penerima</b> dan mengirim notifikasi. "
        "Setelah terbit, isi instruksi tidak dapat diubah.",
        "Pantau di tabel <b>Penerima</b> (kolom <i>Dibaca</i>) dan <b>Tugas yang dihasilkan</b> (status &amp; progres).",
        "Bila perlu dibatalkan: kartu <b>Batalkan instruksi</b>, isi alasan. Semua tugas yang belum selesai ikut dibatalkan.",
    ],
}
T_DISPOSISI = {
    "judul": "Membuat disposisi surat",
    "url": "letters:incoming_list",
    "langkah": [
        "Buka <b>Surat Masuk</b>, klik nomor agenda surat.",
        "Di kartu <b>Buat disposisi</b>: pilih penerima, unit, tulis <b>arahan</b>, prioritas, dan tenggat.",
        "Biarkan <b>Memerlukan tindakan</b> tercentang bila penerima harus mengerjakan sesuatu: sistem membuat tugas "
        "untuknya dan tenggat menjadi wajib. Hapus centang bila disposisi hanya untuk diketahui.",
        "Tekan <b>Kirim disposisi</b>. Anda menjadi pemeriksa tugas yang dihasilkan.",
        "Status disposisi berubah otomatis: Terkirim → Dibaca (saat penerima membukanya) → Ditindaklanjuti → Selesai.",
    ],
}
T_TERUSKAN = {
    "judul": "Menerima dan meneruskan disposisi",
    "url": "letters:disposition_list",
    "langkah": [
        "Buka <b>Disposisi</b> (tautan <i>Belum selesai</i> menyaring yang masih berjalan) lalu klik disposisi.",
        "Bila disposisi memerlukan tindakan, kerjakan <b>Tugas tertaut</b> seperti tugas biasa.",
        "Untuk meneruskan ke bawahan: tekan <b>Teruskan disposisi</b>, isi penerima, arahan, dan tenggat. "
        "Disposisi turunan menyimpan tautan ke disposisi asal.",
    ],
}
T_MONITOR = {
    "judul": "Memakai Beranda",
    "url": "dashboard:home",
    "langkah": [
        "Bagian <b>Perlu Anda kerjakan</b> berisi hal yang menunggu Anda: tugas baru, hasil yang harus diperbaiki, "
        "tenggat yang dekat, hasil kerja yang harus Anda periksa, disposisi, dan instruksi baru. Tekan tombol di "
        "kanan setiap kabar (mis. <b>Lihat &amp; terima</b>, <b>Periksa hasil</b>).",
        "<b>Tugas saya yang sedang berjalan</b> menampilkan tugas Anda beserta progres dan tenggatnya.",
        "Kolom kanan: <b>Agenda hari ini</b> dan <b>Ringkasan tugas</b> (Belum dimulai, Berjalan, Tenggat ≤ H-2, "
        "Terlambat, Terhambat, Menunggu verifikasi, Perlu perbaikan, Selesai). <b>Klik angka</b> untuk membuka daftarnya.",
        "Pimpinan (Direktur, Wakil Direktur, Kepala Unit, Auditor) juga melihat <b>Pantauan</b>: instruksi aktif, "
        "disposisi belum selesai, <b>Tugas terlambat</b>, tugas terhambat, serta <b>Kinerja per unit &amp; tren "
        "penyelesaian</b> (klik judulnya untuk membuka).",
        "Angka selalu dihitung sesuai lingkup akses Anda.",
    ],
}
T_SURAT = {
    "judul": "Mencatat surat masuk",
    "url": "letters:incoming_create",
    "langkah": [
        "Buka <b>Surat Masuk</b> → <b>+ Catat surat masuk</b>.",
        "Isi nomor surat, tanggal surat, tanggal diterima, pengirim, perihal, ringkasan, <b>klasifikasi</b> "
        "(Biasa/Terbatas/Rahasia), dan unggah lampiran pindaian surat. Tekan <b>Simpan</b>.",
        "Nomor agenda (mis. SM/2026/0001) dibuat otomatis. Teruskan ke Direktur/pejabat untuk didisposisikan.",
        "Gunakan kotak <b>Cari</b> dan rentang tanggal diterima untuk menemukan surat.",
    ],
}
T_SURAT_KELUAR = {
    "judul": "Mencatat surat keluar",
    "url": "letters:outgoing_create",
    "langkah": [
        "Buka <b>Surat Keluar</b> → <b>+ Catat surat keluar</b>.",
        "Isi tanggal, penerima, perihal, ringkasan, klasifikasi, dan lampiran. Nomor (mis. SK/2026/0001) dibuat otomatis.",
    ],
}
T_ATAS_NAMA = {
    "judul": "Mencatat instruksi atas nama pimpinan",
    "url": "instructions:create",
    "langkah": [
        "Ikuti langkah membuat instruksi, lalu isi kolom <b>Atas nama</b> dengan Direktur/Wakil Direktur yang "
        "memberi instruksi.",
        "Pihak \"atas nama\" menjadi pemberi instruksi dan <b>pemeriksa</b> tugas-tugasnya; Anda tercatat sebagai pencatat.",
    ],
}
T_AUDIT = {
    "judul": "Memeriksa data dan jejak audit",
    "url": "workflow:list",
    "langkah": [
        "Anda dapat membuka semua tugas, instruksi yang sudah terbit, surat, dan disposisi yang tidak berklasifikasi Rahasia.",
        "Setiap halaman tugas memuat <b>Audit trail</b>: siapa mengubah status, PIC, tenggat, verifikasi, dan "
        "pembatalan, kapan, beserta alasannya.",
        "Unduhan bukti/lampiran juga tercatat di audit trail.",
        "Akun auditor hanya-baca: tombol perubahan tidak tersedia dan permintaan perubahan ditolak sistem.",
    ],
}
T_ADMIN = {
    "judul": "Mengelola akun, unit, dan atasan",
    "url": "pengguna:index",
    "langkah": [
        "<b>Struktur Organisasi</b> (menu kiri, bagian Kelola): pohon unit RSI Yatofa. Tambah sub-unit (ikon +), ubah kode/nama/jenis/"
        "<b>induk struktural</b>/urutan/kepala unit, kelola <b>hubungan koordinasi/pengawasan</b> (mis. komite → Direktur), "
        "dan <b>nonaktifkan</b> unit (alasan wajib; tidak bisa selama masih punya sub-unit aktif). Sistem menolak induk "
        "yang membuat hubungan melingkar. Unit tidak pernah dihapus.",
        "Induk struktural menentukan lingkup akses atasan dan eskalasi; hubungan koordinasi/pengawasan hanya informasi.",
        "<b>Pengguna</b> (menu kiri, bagian Kelola, khusus Administrator): klik ikon <b>tambah pengguna</b> pada unit/bidang di "
        "Master Organisasi, atau <b>+ Tambah pengguna</b> lalu pilih unit dari daftar bertingkat. Isi nama, login, dan "
        "kata sandi; centang <b>Kepala/pimpinan unit ini</b> bila orang tersebut kepalanya. <b>Jabatan</b>, <b>peran</b>, "
        "dan <b>atasan langsung</b> terisi otomatis dari struktur (tetap bisa diubah). Tombol <b>Simpan &amp; tambah lagi "
        "di unit ini</b> mempercepat input satu bidang.",
        "Atasan langsung adalah penerima <b>eskalasi</b> keterlambatan; bila kosong, eskalasi dikirim ke kepala unit. "
        "Daftar Pengguna dikelompokkan per bidang dan menampilkan unit yang <b>belum ada pengguna</b>.",
        "Pegawai keluar/pindah: <b>Nonaktifkan</b> pengguna (tidak bisa login, riwayat tetap utuh; jabatan kepala unit "
        "dilepas otomatis). Pindah unit cukup dengan mengubah unitnya.",
        "<b>Pengaturan Aplikasi</b>: <b>Mode Demo</b> memuat pegawai dan data contoh (otomatis sekali saat aplikasi "
        "pertama dipasang). Menjelang launching, login dengan akun administrator <b>asli</b> (bukan akun demo_), ketik "
        "<b>RESET DATA DEMO</b>, lalu tekan <b>Reset data demo</b>: semua data demo terhapus dan aplikasi masuk "
        "<b>Mode Produksi</b>, sehingga pembaruan berikutnya tidak memuat data contoh lagi.",
        "Pantau <b>Reminder logs</b> (status Terkirim/Gagal, jumlah percobaan) dan <b>Log audit</b> (hanya-baca, "
        "tidak dapat diubah atau dihapus).",
        "Pengguna lupa password? Isi <b>Kata sandi baru</b> di halaman ubah pengguna (aplikasi tidak menyediakan "
        "reset mandiri).",
    ],
}

T_AGENDA = {
    "judul": "Membuat dan mengelola agenda",
    "url": "agenda:create",
    "langkah": [
        "Buka <b>Agenda</b> → <b>+ Agenda baru</b> (atau klik <b>+</b> pada tanggal di <b>Kalender</b>).",
        "Isi judul, <b>jenis</b> (Rapat, Kegiatan, Kunjungan/tamu, Lainnya), waktu mulai &amp; selesai, lokasi dan/atau "
        "tautan rapat daring, <b>pimpinan/penyelenggara</b>, <b>peserta</b> (tahan Ctrl untuk memilih banyak), catatan "
        "acara, dan klasifikasi. Tekan <b>Simpan &amp; kirim undangan</b> — semua peserta menerima notifikasi undangan.",
        "Pimpinan/penyelenggara rapat adalah orang yang kelak <b>menyetujui notulen</b> dan memeriksa tindak lanjutnya.",
        "Perubahan waktu/lokasi lewat <b>Ubah jadwal/peserta</b>: peserta lama mendapat notifikasi <i>Perubahan jadwal</i>, "
        "peserta baru mendapat undangan.",
        "<b>Tandai selesai</b> setelah kegiatan berlangsung (rapat otomatis selesai saat notulennya disetujui). "
        "<b>Batalkan agenda</b> wajib disertai alasan; peserta diberi tahu.",
        "Pengingat agenda dikirim otomatis {hari_agenda} pukul {jam_pengingat}.00 ke penyelenggara dan peserta.",
    ],
}
T_AGENDA_PESERTA = {
    "judul": "Sebagai peserta agenda",
    "url": "agenda:list",
    "langkah": [
        "Undangan, perubahan jadwal, pembatalan, dan pengingat masuk ke <b>Notifikasi</b>.",
        "Buka <b>Agenda</b> (daftar <i>Hari ini &amp; mendatang</i>) atau <b>Kalender</b> untuk melihat jadwal Anda.",
        "Di halaman agenda, unduh <b>bahan rapat</b> atau unggah bahan Anda lewat kartu <b>Unggah bahan</b>.",
    ],
}
T_NOTULEN_TULIS = {
    "judul": "Menulis notulen dan butir keputusan",
    "url": "notulen:list",
    "langkah": [
        "Buka agenda berjenis <b>Rapat</b> → <b>Tulis notulen</b>. Yang dapat menulis: sekretariat, pembuat/penyelenggara "
        "agenda, Direktur, atau Wakil Direktur/Kepala Unit yang menjadi peserta.",
        "Isi <b>peserta hadir</b>, peserta lain/tamu, <b>pokok pembahasan</b>, ringkasan, dan lampiran → <b>Simpan draf</b>.",
        "Kartu <b>Tambah keputusan</b>: tulis keputusan. Bila perlu dikerjakan, biarkan <b>Memerlukan tindakan</b> "
        "tercentang dan isi prioritas, <b>tenggat</b> (wajib), dan kriteria selesai. Hapus centang untuk keputusan "
        "yang hanya untuk diketahui.",
        "Pada setiap keputusan yang memerlukan tindakan, pilih unit dan PIC lalu <b>Tambah PIC</b> (boleh lebih dari satu).",
        "Tekan <b>Ajukan untuk persetujuan</b>. Sistem menolak bila ada keputusan bertindakan yang belum punya PIC.",
        "Bila dikembalikan, catatan pimpinan rapat tampil di atas notulen; perbaiki lalu ajukan ulang (nomor revisi naik).",
    ],
}
T_NOTULEN_SETUJUI = {
    "judul": "Menyetujui notulen (pimpinan rapat)",
    "url": "notulen:list",
    "langkah": [
        "Anda menerima notifikasi <i>Notulen menunggu persetujuan</i>. Buka notulennya.",
        "Periksa pembahasan, keputusan, PIC, dan tenggat. Pilih <b>Setujui &amp; buat tindak lanjut</b> atau "
        "<b>Kembalikan ke notulis</b> (catatan wajib).",
        "Saat disetujui: isi notulen terkunci, rapat ditandai selesai, dan <b>setiap PIC keputusan mendapat satu tugas</b> "
        "dengan Anda sebagai pemeriksa. Persetujuan ulang tidak membuat tugas ganda.",
        "Tekan <b>Cetak</b> untuk mencetak/menyimpan PDF notulen resmi.",
    ],
}
T_TINDAKLANJUT = {
    "judul": "Memantau tindak lanjut keputusan rapat",
    "url": "tindaklanjut:index",
    "langkah": [
        "Buka <b>Tindak Lanjut</b>. Tampil ringkasan <b>per rapat</b> dan <b>per unit</b> (total, selesai, belum, terlambat) "
        "serta daftar seluruh tindak lanjut yang boleh Anda lihat.",
        "Saring dengan <b>Status</b> (Belum selesai, Terlambat, atau status tertentu), <b>Unit</b>, dan rentang tanggal rapat.",
        "Klik <b>rincian</b> pada sebuah rapat untuk melihat per keputusan: PIC, progres, status, dan catatan terakhir.",
        "Untuk rapat evaluasi berikutnya: <b>Cetak daftar belum selesai</b>.",
        "Tindak lanjut adalah tugas biasa: PIC mengerjakannya di <b>Tugas</b> dan pimpinan rapat "
        "memverifikasinya. Gunakan <b>Minta pembaruan ke PIC</b> atau kembalikan hasil untuk klarifikasi/revisi.",
    ],
}
T_ARSIP_CARI = {
    "judul": "Mencari dan membuka arsip",
    "url": "arsip:list",
    "langkah": [
        "Buka menu <b>Arsip Dokumen</b>. Saring dengan <b>Cari</b> (judul, nomor, kata kunci), <b>Jenis</b>, <b>Unit</b>, <b>Tahun</b>, "
        "dan <b>Status</b>.",
        "Halaman dokumen menampilkan metadata, tautan ke <b>objek asal</b> (surat/instruksi/tugas/rapat), semua "
        "<b>versi berkas</b>, dan aktivitas. Setiap unduhan tercatat.",
        "Dokumen yang berasal dari modul lain mengikuti hak akses objek asalnya; dokumen Rahasia hanya untuk pihak yang berhak.",
    ],
}
T_ARSIP_KELOLA = {
    "judul": "Mengelola arsip (petugas arsip & sekretariat)",
    "url": "arsip:create",
    "langkah": [
        "Arsip <b>otomatis</b>: lampiran surat masuk/keluar, lampiran instruksi, bahan agenda, notulen yang disetujui, "
        "dan bukti tugas langsung tercatat tanpa perlu diunggah ulang.",
        "Arsip <b>manual</b>: <b>Arsip Dokumen</b> → <b>+ Arsipkan dokumen</b>; isi jenis, nomor, tanggal dokumen, judul, unit, "
        "klasifikasi, kata kunci, dan berkas → <b>Simpan ke arsip</b>.",
        "Revisi dokumen manual: kartu <b>Unggah versi baru</b> dengan <b>catatan versi</b> (wajib). Versi lama tetap tersimpan. "
        "Versi dokumen otomatis mengikuti objek asalnya.",
        "Perbaiki metadata lewat <b>Simpan metadata</b>; perubahan tercatat.",
        "Masa retensi = tanggal dokumen + {tahun_retensi} tahun (dapat diatur per jenis). Saring <b>Status: Lewat masa "
        "retensi</b> untuk melihat dokumen yang dapat diusulkan musnah.",
        "Petugas arsip menekan <b>Usulkan pemusnahan</b> (alasan wajib); Direktur diberi tahu.",
    ],
}
T_ARSIP_MUSNAH = {
    "judul": "Memutuskan pemusnahan arsip (Direktur)",
    "url": "arsip:list",
    "langkah": [
        "Anda menerima notifikasi <i>Usulan pemusnahan arsip</i>. Buka dokumennya.",
        "Di kartu <b>Keputusan pemusnahan</b> pilih <b>Setujui pemusnahan</b> (isi berita acara — wajib) atau "
        "<b>Tolak usulan</b>, lalu <b>Simpan keputusan</b>.",
        "Dokumen yang dimusnahkan tetap tercatat (metadata &amp; berita acara), tetapi berkasnya tidak dapat diunduh lagi. "
        "Tidak ada penghapusan dokumen dari aplikasi.",
    ],
}
T_LAPORAN = {
    "judul": "Membuat laporan pelaksanaan & evaluasi unit",
    "url": "laporan:index",
    "langkah": [
        "Buka <b>Laporan</b>. Atur <b>Dari/Sampai tanggal</b> (tugas yang dibuat pada periode itu), dan bila perlu "
        "<b>Unit</b>, <b>PIC</b>, <b>Jenis pekerjaan</b>, <b>Status</b> → <b>Tampilkan</b>.",
        "Laporan memuat ringkasan (total, selesai, selesai &amp; diverifikasi vs tanpa verifikasi, menunggu verifikasi, "
        "terhambat, terlambat, tingkat penyelesaian, <b>persentase tepat waktu</b>, rata-rata hari penyelesaian), "
        "instruksi &amp; disposisi per status, tindak lanjut rapat, serta tabel <b>per unit</b>, <b>per jenis</b>, "
        "<b>per PIC</b>, dan daftar tugas terlambat.",
        "Waktu pembuatan dan parameter filter tercetak di laporan. Angka mengikuti lingkup akses Anda.",
        "<b>Excel</b> mengunduh berkas .xlsx; <b>Cetak/PDF</b> membuka versi cetak (pilih <i>Simpan sebagai PDF</i> di "
        "dialog cetak); <b>Simpan ke arsip</b> menyimpan Excel-nya ke E-Arsip.",
    ],
}

# --------------------------------------------------------------------------- panduan per peran
PERAN = [
    {
        "kode": Role.DIREKTUR, "ikon": "bi-person-badge",
        "ringkas": "Memberi arahan (instruksi & disposisi), memverifikasi hasil, dan memantau seluruh pekerjaan "
                   "rumah sakit dari dashboard.",
        "lingkup": "Melihat <b>semua</b> data, termasuk yang berklasifikasi Rahasia.",
        "tugas": [T_MONITOR, T_INSTRUKSI, T_DISPOSISI, T_VERIFIKASI, T_KENDALI, T_AGENDA, T_NOTULEN_SETUJUI,
                  T_TINDAKLANJUT, T_LAPORAN, T_ARSIP_MUSNAH, T_LANGSUNG, T_NOTIF],
        "tidak": ["Administrasi akun dilakukan oleh Administrator Sistem.",
                  "Mengusulkan pemusnahan arsip (dilakukan Petugas Arsip; Direktur yang memutuskan)."],
    },
    {
        "kode": Role.WADIR, "ikon": "bi-diagram-3",
        "ringkas": "Mengawasi bidang dan unit-unit di bawahnya, meneruskan disposisi, menerbitkan instruksi bidang, "
                   "dan memverifikasi pekerjaan yang ditugaskannya.",
        "lingkup": "Tugas di unit Anda dan seluruh sub-unitnya (kecuali Rahasia yang tidak melibatkan Anda), ditambah "
                   "tugas yang Anda buat, periksa, atau kerjakan.",
        "tugas": [T_MONITOR, T_TERUSKAN, T_DISPOSISI, T_INSTRUKSI, T_LANGSUNG, T_VERIFIKASI, T_KENDALI, T_AGENDA,
                  T_NOTULEN_TULIS, T_NOTULEN_SETUJUI, T_TINDAKLANJUT, T_LAPORAN, T_KERJAKAN, T_NOTIF],
        "tidak": ["Melihat dokumen Rahasia yang tidak melibatkan Anda.",
                  "Mencatat surat masuk/keluar (dilakukan sekretariat/petugas arsip)."],
    },
    {
        "kode": Role.KEPALA_UNIT, "ikon": "bi-people",
        "ringkas": "Membagi pekerjaan ke staf, meneruskan disposisi, memantau unit, memverifikasi hasil staf, dan "
                   "menerima eskalasi keterlambatan staf.",
        "lingkup": "Tugas di unit Anda dan sub-unitnya (kecuali Rahasia yang tidak melibatkan Anda), ditambah tugas "
                   "yang Anda buat, periksa, atau kerjakan.",
        "tugas": [T_LANGSUNG, T_TERUSKAN, T_VERIFIKASI, T_KENDALI, T_KERJAKAN, T_AGENDA, T_NOTULEN_TULIS,
                  T_TINDAKLANJUT, T_LAPORAN, T_MONITOR, T_NOTIF],
        "tidak": ["Menerbitkan instruksi (default: hanya Direktur, Wakil Direktur, Sekretaris).",
                  "Mengendalikan tugas di mana Anda sendiri PIC-nya — itu dilakukan atasan Anda."],
    },
    {
        "kode": Role.STAF, "ikon": "bi-person-workspace",
        "ringkas": "Melaksanakan tugas: menerima, melaporkan progres dan hambatan, mengunggah bukti, mengirim hasil.",
        "lingkup": "Tugas di mana Anda PIC atau kolaborator, serta instruksi/disposisi yang ditujukan kepada Anda.",
        "tugas": [T_NOTIF, T_KERJAKAN, T_PERBAIKAN, T_KOLABORATOR, T_AGENDA_PESERTA, T_TINDAKLANJUT, T_ARSIP_CARI],
        "tidak": ["Membuat penugasan, instruksi, atau disposisi.",
                  "Membatalkan atau mengubah PIC/tenggat tugas Anda — minta atasan bila tenggat perlu diubah.",
                  "Melihat tugas staf/unit lain."],
    },
    {
        "kode": Role.SEKRETARIS, "ikon": "bi-journal-text",
        "ringkas": "Administrasi persuratan Direktur dan pencatatan instruksi atas nama pimpinan.",
        "lingkup": "Surat dan disposisi yang tidak berklasifikasi Rahasia, surat yang Anda catat, dan instruksi yang Anda buat.",
        "tugas": [T_SURAT, T_SURAT_KELUAR, T_ATAS_NAMA, T_INSTRUKSI, T_AGENDA, T_NOTULEN_TULIS, T_ARSIP_KELOLA,
                  T_ARSIP_CARI, T_NOTIF],
        "tidak": ["Membuat disposisi atau penugasan langsung (dilakukan pejabat).",
                  "Menyetujui notulen (dilakukan pimpinan rapat).",
                  "Melihat surat Rahasia yang tidak Anda catat."],
    },
    {
        "kode": Role.ARSIP, "ikon": "bi-archive",
        "ringkas": "Mencatat dan menata surat masuk/keluar beserta lampirannya.",
        "lingkup": "Surat masuk/keluar yang tidak berklasifikasi Rahasia dan surat yang Anda catat.",
        "tugas": [T_ARSIP_KELOLA, T_ARSIP_CARI, T_SURAT, T_SURAT_KELUAR, T_NOTIF],
        "tidak": ["Memutuskan pemusnahan arsip (wewenang Direktur).", "Melihat arsip Rahasia yang bukan milik Anda."],
    },
    {
        "kode": Role.AUDITOR, "ikon": "bi-search",
        "ringkas": "Memeriksa data dan jejak audit tanpa mengubah apa pun.",
        "lingkup": "Semua data yang tidak berklasifikasi Rahasia (hanya-baca).",
        "tugas": [T_AUDIT, T_MONITOR, T_LAPORAN, T_ARSIP_CARI, T_TINDAKLANJUT],
        "tidak": ["Mengubah, memverifikasi, membatalkan, atau membuat data apa pun.", "Melihat dokumen Rahasia."],
    },
    {
        "kode": Role.ADMIN, "ikon": "bi-gear",
        "ringkas": "Mengelola akun, peran, unit kerja, atasan langsung, dan memantau log teknis.",
        "lingkup": "Administrasi teknis. Data operasional (tugas/surat) hanya terlihat bila Anda terlibat.",
        "tugas": [T_ADMIN, T_NOTIF],
        "tidak": ["Mengubah atau menghapus log audit.",
                  "Data operasional bukan wewenang administrator — jangan mengubahnya lewat Administrasi."],
    },
]

FAQ = [
    ("Mengapa saya tidak melihat tugas tertentu?",
     "Daftar dan dashboard hanya menampilkan data dalam lingkup akses Anda (lihat bagian <i>Yang dapat Anda lihat</i> "
     "pada peran Anda). Membuka alamat tugas di luar lingkup akan menampilkan \"tidak ditemukan\"."),
    ("Mengapa tombol tertentu tidak muncul?",
     "Tombol hanya tampil bila peran dan posisi Anda dalam tugas mengizinkan (mis. kartu Verifikasi hanya untuk "
     "pemeriksa, saat status Menunggu verifikasi). Sistem juga memeriksa izin di server."),
    ("Progres sudah 100%, mengapa belum selesai?",
     "Tugas baru selesai setelah PIC menekan <b>Kirim untuk verifikasi</b> dan pemeriksa menyetujui."),
    ("Kapan pengingat dikirim?",
     "Setiap hari pukul {jam_pengingat}.00: {hari_pengingat} sebelum tenggat ke PIC, saat tenggat terlewati, dan "
     "eskalasi ke atasan bila terlambat ≥ {hari_eskalasi} hari. Pengingat tidak dikirim ganda dan berhenti saat "
     "tugas selesai atau dibatalkan."),
    ("Tenggat saya tidak realistis. Bagaimana?",
     "Laporkan sebagai <b>Terhambat</b> dengan penjelasan, atau minta pemberi tugas mengubah tenggat. Perubahan "
     "tenggat wajib beralasan dan tercatat."),
    ("Berkas apa saja yang boleh diunggah?",
     "{jenis_berkas}, maksimal {ukuran_berkas} MB per berkas. Berkas disimpan terlindungi dan hanya dapat diunduh "
     "oleh pengguna yang berhak; setiap unduhan tercatat."),
    ("Mengapa notifikasi menulis \"(rahasia)\"?",
     "Untuk dokumen berklasifikasi Rahasia, judul tidak ditampilkan di notifikasi. Buka notifikasinya untuk melihat isi."),
    ("Siapa yang boleh menerbitkan instruksi?",
     "Saat ini: {penerbit_instruksi}. Aturan ini dapat diubah oleh pengelola sistem."),
    ("Mengapa keputusan rapat belum menjadi tugas?",
     "Tugas tindak lanjut baru dibuat setelah notulen <b>disetujui</b> pimpinan rapat, dan hanya untuk keputusan yang "
     "ditandai <i>memerlukan tindakan</i> serta sudah memiliki PIC."),
    ("Apakah saya perlu mengunggah ulang dokumen ke E-Arsip?",
     "Tidak. Lampiran surat, instruksi, bahan rapat, notulen yang disetujui, dan bukti tugas diarsipkan otomatis. "
     "E-Arsip manual hanya untuk dokumen yang tidak berasal dari modul lain."),
    ("Bisakah arsip dihapus?",
     "Tidak. Arsip hanya dapat dimusnahkan setelah masa retensi ({tahun_retensi} tahun) lewat usulan Petugas Arsip dan "
     "persetujuan Direktur; catatan dan berita acaranya tetap disimpan."),
    ("Lupa password atau akun terkunci?", "Hubungi Administrator Sistem."),
]


# --------------------------------------------------------------------------- panduan per modul (12 modul PRD)
MODUL = [
    {"no": 1, "nama": "E-Surat", "ikon": "bi-envelope-paper", "url": "letters:incoming_list",
     "fungsi": "Mencatat surat masuk dan keluar beserta nomor agenda/nomor surat otomatis, klasifikasi, dan lampiran.",
     "siapa": "Sekretaris, Petugas Arsip, dan Direktur mencatat; pihak yang menerima disposisi dapat melihat suratnya.",
     "tugas": [T_SURAT, T_SURAT_KELUAR],
     "aturan": ["Nomor agenda SM/tahun/urut dan nomor surat keluar SK/tahun/urut dibuat otomatis.",
                "Lampiran disimpan terlindungi dan otomatis masuk E-Arsip.",
                "Surat Rahasia hanya dapat dilihat Direktur, pencatat, dan penerima disposisinya."]},
    {"no": 2, "nama": "E-Disposisi", "ikon": "bi-signpost-split", "url": "letters:disposition_list",
     "fungsi": "Memberi arahan atas surat masuk kepada pejabat/unit, meneruskannya berjenjang, dan menjadikannya tugas.",
     "siapa": "Direktur, Wakil Direktur, dan Kepala Unit memberi/meneruskan; penerima menindaklanjuti.",
     "tugas": [T_DISPOSISI, T_TERUSKAN],
     "aturan": ["Disposisi yang memerlukan tindakan wajib bertenggat dan otomatis menjadi satu tugas.",
                "Status mengikuti tugas: Terkirim → Dibaca → Ditindaklanjuti → Selesai.",
                "Hanya penerima disposisi yang dapat meneruskannya."]},
    {"no": 3, "nama": "E-Instruksi", "ikon": "bi-megaphone", "url": "instructions:list",
     "fungsi": "Mencatat seluruh perintah Direktur secara resmi: kode unik, penerima, tenggat, bukti, dan status baca.",
     "siapa": "{penerbit_instruksi} membuat; penerima (unit + PIC) melaksanakan.",
     "tugas": [T_INSTRUKSI, T_ATAS_NAMA],
     "aturan": ["Setelah terbit, isi tidak dapat diubah; perubahan lewat pembatalan beralasan.",
                "Satu tugas untuk setiap penerima; pembatalan instruksi membatalkan tugas yang belum selesai.",
                "Instruksi tercatat dibaca saat PIC membuka instruksi atau tugasnya."]},
    {"no": 4, "nama": "E-Task Management", "ikon": "bi-list-check", "url": "workflow:list",
     "fungsi": "Satu mesin tugas untuk semua pekerjaan: PIC, kolaborator, prioritas, tenggat, kriteria selesai, bukti, verifikasi.",
     "siapa": "Atasan membuat penugasan langsung; PIC dan kolaborator mengerjakan; pemberi tugas memverifikasi.",
     "tugas": [T_LANGSUNG, T_KERJAKAN, T_VERIFIKASI, T_PERBAIKAN],
     "aturan": ["Penugasan langsung wajib beralasan dan bertenggat.",
                "Progres 100% tidak menutup tugas; penutupan lewat kirim hasil dan verifikasi.",
                "Bukti wajib (bila dicentang) sebelum hasil dapat dikirim."]},
    {"no": 5, "nama": "E-Monitoring", "ikon": "bi-binoculars", "url": "workflow:list",
     "fungsi": "Memantau progres, hambatan, status, tenggat, dan sumber seluruh pekerjaan; meminta pembaruan dan mengendalikan tugas.",
     "siapa": "Pimpinan dan atasan unit (sesuai lingkup); PIC memantau tugasnya sendiri.",
     "tugas": [T_KENDALI],
     "aturan": ["Filter: status, penanda (terlambat, H-2, belum ditutup), sumber, prioritas, unit, PIC, rentang tenggat.",
                "Progres yang dilaporkan PIC dipisahkan dari keputusan penutupan oleh pemeriksa.",
                "Perubahan PIC/tenggat dan pembatalan wajib beralasan dan tercatat di audit trail."]},
    {"no": 6, "nama": "E-Reminder", "ikon": "bi-alarm", "url": "notifications:list",
     "fungsi": "Pengingat dan eskalasi otomatis sehingga keterlambatan tidak perlu dicari manual.",
     "siapa": "Berjalan otomatis setiap hari pukul {jam_pengingat}.00; semua pengguna menerima notifikasi yang relevan.",
     "tugas": [T_NOTIF],
     "aturan": ["Tugas: pengingat {hari_pengingat} sebelum tenggat ke PIC; notifikasi saat terlambat; eskalasi ke "
                "atasan langsung PIC (atau kepala unit) bila terlambat ≥ {hari_eskalasi} hari.",
                "Agenda: pengingat {hari_agenda} ke penyelenggara dan peserta.",
                "Tidak ada pengingat ganda; berhenti saat tugas selesai/dibatalkan; kegagalan kirim dicatat dan dicoba ulang.",
                "Kanal saat ini: notifikasi internal (email/WhatsApp setelah disetujui)."]},
    {"no": 7, "nama": "E-Agenda", "ikon": "bi-calendar-event", "url": "agenda:list",
     "fungsi": "Jadwal Direktur, rapat, dan kegiatan: undangan, perubahan jadwal, pembatalan, bahan rapat, dan kalender.",
     "siapa": "Direktur, Wakil Direktur, Kepala Unit, dan Sekretaris membuat; peserta menerima undangan dan bahan.",
     "tugas": [T_AGENDA, T_AGENDA_PESERTA],
     "aturan": ["Agenda hanya terlihat oleh pembuat, penyelenggara, peserta, Direktur, serta sekretariat/auditor (non-Rahasia).",
                "Hanya pembuat, penyelenggara, atau Direktur yang dapat mengubah/membatalkan.",
                "Agenda berjenis Rapat dapat dibuatkan notulen."]},
    {"no": 8, "nama": "E-Notulen & Keputusan", "ikon": "bi-journal-check", "url": "notulen:list",
     "fungsi": "Mencatat hasil rapat dan keputusan terstruktur; keputusan yang perlu tindakan menjadi tugas setelah disetujui.",
     "siapa": "Notulis (sekretariat/pejabat peserta) menulis; pimpinan rapat menyetujui atau mengembalikan.",
     "tugas": [T_NOTULEN_TULIS, T_NOTULEN_SETUJUI],
     "aturan": ["Alur: Draf → Diajukan → Disetujui (dapat dikembalikan dengan catatan; nomor revisi bertambah).",
                "Keputusan bertindakan wajib bertenggat dan ber-PIC sebelum diajukan.",
                "Notulen yang disetujui terkunci, dapat dicetak, dan masuk E-Arsip bila berlampiran."]},
    {"no": 9, "nama": "E-Follow Up", "ikon": "bi-arrow-repeat", "url": "tindaklanjut:index",
     "fungsi": "Mengelola tindak lanjut keputusan rapat: ringkasan per rapat/unit/periode dan daftar yang belum selesai.",
     "siapa": "Pimpinan rapat dan atasan memantau; PIC mengerjakan lewat Tugas.",
     "tugas": [T_TINDAKLANJUT],
     "aturan": ["Tindak lanjut adalah tugas yang sama (tidak dicatat terpisah), tertaut ke keputusan dan rapat asalnya.",
                "Pengingat, eskalasi, bukti, dan verifikasi berlaku seperti tugas lain."]},
    {"no": 10, "nama": "E-Arsip", "ikon": "bi-archive", "url": "arsip:list",
     "fungsi": "Menyimpan atau merujuk seluruh dokumen dan bukti pekerjaan dengan metadata, versi, hak akses, dan retensi.",
     "siapa": "Petugas Arsip dan Sekretaris mengelola; Direktur memutuskan pemusnahan; pengguna lain mencari sesuai hak.",
     "tugas": [T_ARSIP_CARI, T_ARSIP_KELOLA, T_ARSIP_MUSNAH],
     "aturan": ["Retensi bawaan {tahun_retensi} tahun sejak tanggal dokumen (menunggu kebijakan RS; dapat diatur per jenis).",
                "Tidak ada penghapusan; pemusnahan dua langkah (usul → setuju) dengan berita acara.",
                "Setiap unduhan dan perubahan metadata tercatat."]},
    {"no": 11, "nama": "E-Reporting", "ikon": "bi-bar-chart-line", "url": "laporan:index",
     "fungsi": "Laporan pelaksanaan dan evaluasi unit per periode, unit, PIC, jenis pekerjaan, dan status; ekspor Excel/PDF.",
     "siapa": "Pimpinan, sekretaris, petugas arsip, dan auditor (menu Laporan); angka sesuai lingkup akses masing-masing.",
     "tugas": [T_LAPORAN],
     "aturan": ["Membedakan pekerjaan yang sudah ditutup dari yang masih menunggu verifikasi.",
                "Persentase tepat waktu = selesai sebelum/pada tenggat dibagi tugas selesai yang bertenggat.",
                "Laporan dapat disimpan ke E-Arsip sebagai dokumen jenis Laporan."]},
    {"no": 12, "nama": "Executive Dashboard", "ikon": "bi-speedometer2", "url": "dashboard:home",
     "fungsi": "Beranda: daftar hal yang perlu Anda kerjakan, tugas Anda, agenda, ringkasan tugas; pimpinan juga melihat pantauan unit.",
     "siapa": "Semua pengguna (halaman awal, menu Beranda); isi mengikuti lingkup akses.",
     "tugas": [T_MONITOR],
     "aturan": ["Setiap angka dapat diklik dan membuka daftar dengan filter yang sama.",
                "Agenda hari ini dan 7 hari ke depan; tindak lanjut rapat yang belum selesai dan terlambat."]},
]
