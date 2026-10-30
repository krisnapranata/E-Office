"""Data CONTOH RSI Yatofa untuk demo/presentasi: pegawai fiktif per unit Master Organisasi + isian semua alur.

- Nama pegawai FIKTIF (bukan pegawai asli); semua login berawalan `demo_`.
- Semua isian dibuat lewat fungsi layanan aplikasi (notifikasi, audit trail, arsip otomatis ikut terbentuk).
- Idempotent: akun dicari per username; isian alur hanya dibuat sekali (dilewati bila sudah ada).
- `nonaktifkan_demo()` menonaktifkan semua akun demo (data tidak dihapus).
"""
from datetime import datetime, time, timedelta

from django.contrib.auth.password_validation import validate_password
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.utils import timezone

from .models import OrganizationUnit, Role, User
from .organisasi import seed_rsiy
from .pengguna import atasan_saran, jabatan_saran, peran_saran

AWALAN = "demo_"

# (kode unit, username tanpa awalan, nama lengkap, kepala?, peran khusus, jabatan khusus)
# Urutan = urutan bagan (induk dulu) agar atasan langsung dapat diisi dari kepala unit induk.
PEGAWAI = [
    ("RSIY-DIR", "ahmad.fauzi", "dr. H. Ahmad Fauzi, M.Kes", True, None, None),
    ("RSIY-DIR", "siti.nurhaliza", "Siti Nurhaliza, A.Md", False, Role.SEKRETARIS, "Sekretaris Direktur"),
    ("RSIY-SPI", "bambang.supriyadi", "Drs. Bambang Supriyadi, Ak.", True, Role.AUDITOR, None),
    ("RSIY-KMEDIK", "hendra.wijaya", "dr. Hendra Wijaya, Sp.PD", True, None, None),
    ("RSIY-KKEP", "sri.wahyuni", "Ns. Sri Wahyuni, S.Kep", True, None, None),
    ("RSIY-KPPI", "rina.kartika", "dr. Rina Kartika, Sp.MK", True, None, None),
    ("RSIY-KKESLAIN", "yuni.astuti", "Yuni Astuti, S.Gz", True, None, None),
    ("RSIY-K3RS", "agus.salim", "Agus Salim, S.KM", True, None, None),
    ("RSIY-KMKP", "nurul.hidayah", "dr. Nurul Hidayah, MARS", True, None, None),
    ("RSIY-KFT", "lukman.hakim", "apt. Lukman Hakim, S.Farm", True, None, None),
    ("RSIY-KETIK", "imam.santoso", "dr. Imam Santoso, Sp.OG", True, None, None),
    ("RSIY-KPPRA", "fitri.handayani", "dr. Fitri Handayani, Sp.A", True, None, None),
    ("RSIY-CASEMIX", "rudi.hartono", "Rudi Hartono, S.Kom", True, None, "Koordinator Casemix & Asuransi"),
    ("RSIY-CASEMIX", "ayu.pratiwi", "Ayu Pratiwi, A.Md.RMIK", False, None, None),
    # C. Bidang Pelayanan
    ("RSIY-BYAN", "budi.santoso", "dr. Budi Santoso, MM", True, None, None),
    ("RSIY-MGRPP", "indah.permatasari", "dr. Indah Permatasari, MARS", True, None, None),
    ("RSIY-SMEDIK", "arif.rahman", "dr. Arif Rahman", True, None, None),
    ("RSIY-IRNA", "wahyu.hidayat", "Ns. Wahyu Hidayat, S.Kep", True, None, None),
    ("RSIY-IRNA", "rizki.amalia", "Ns. Rizki Amalia, S.Kep", False, None, None),
    ("RSIY-IRJA", "maya.sari", "dr. Maya Sari", True, None, None),
    ("RSIY-IRJA", "ani.rahmawati", "Ani Rahmawati, A.Md.Kep", False, None, None),
    ("RSIY-IBS", "teguh.prasetyo", "dr. Teguh Prasetyo, Sp.B", True, None, None),
    ("RSIY-IBS", "dedi.kurniawan", "Ns. Dedi Kurniawan, S.Kep", False, None, None),
    ("RSIY-IGD", "eko.saputra", "dr. Eko Saputra", True, None, None),
    ("RSIY-IGD", "fajar.nugroho", "Ns. Fajar Nugroho, S.Kep", False, None, None),
    ("RSIY-IGD", "lina.marlina", "Ns. Lina Marlina, S.Kep", False, None, None),
    ("RSIY-SPENUNJANG", "ratna.dewi", "dr. Ratna Dewi", True, None, None),
    ("RSIY-GIZI", "yuliana", "Yuliana, S.Gz", True, None, None),
    ("RSIY-GIZI", "sri.mulyani", "Sri Mulyani, A.Md.Gz", False, None, None),
    ("RSIY-FARMASI", "dian.purnamasari", "apt. Dian Purnamasari, S.Farm", True, None, None),
    ("RSIY-FARMASI", "rahmat.hidayat", "apt. Rahmat Hidayat, S.Farm", False, None, None),
    ("RSIY-FARMASI", "nita.anggraini", "Nita Anggraini, A.Md.Farm", False, None, None),
    ("RSIY-LAB", "herlina", "dr. Herlina, Sp.PK", True, None, None),
    ("RSIY-LAB", "andi.setiawan", "Andi Setiawan, A.Md.AK", False, None, None),
    ("RSIY-RAD", "gunawan", "dr. Gunawan, Sp.Rad", True, None, None),
    ("RSIY-RAD", "hadi.susanto", "Hadi Susanto, A.Md.Rad", False, None, None),
    ("RSIY-CSSD", "endang.susilowati", "Ns. Endang Susilowati, S.Kep", True, None, None),
    ("RSIY-RMSIM", "muhammad.iqbal", "Muhammad Iqbal, S.Kom", True, None, None),
    ("RSIY-RMSIM", "dimas.aditya", "Dimas Aditya, S.Kom", False, Role.ADMIN, "Administrator Sistem E-Office"),
    ("RSIY-RMSIM", "putri.ramadhani", "Putri Ramadhani, A.Md.RMIK", False, None, None),
    ("RSIY-KESLING", "suharto", "Suharto, S.KM", True, None, None),
    ("RSIY-SKEP", "kartini", "Ns. Hj. Kartini, S.Kep, M.Kep", True, None, None),
    ("RSIY-ASKEP", "retno.wulandari", "Ns. Retno Wulandari, S.Kep", True, None, "Koordinator Asuhan Keperawatan"),
    ("RSIY-ETIKMUTU", "yanti.susanti", "Ns. Yanti Susanti, S.Kep", True, None, "Koordinator Etik dan Mutu"),
    # D. Bidang Keuangan
    ("RSIY-BKEU", "hendro.kusumo", "Hendro Kusumo, SE, Ak", True, None, None),
    ("RSIY-ANGGARAN", "novita.sari", "Novita Sari, SE", True, None, "Koordinator Perencanaan Anggaran"),
    ("RSIY-AKUNTANSI", "taufik.hidayat", "Taufik Hidayat, SE", True, None, "Koordinator Akuntansi & Pelaporan"),
    ("RSIY-AKUNTANSI", "mega.puspita", "Mega Puspita, SE", False, None, None),
    ("RSIY-BENDAHARA", "rina.wati", "Rina Wati, SE", True, None, "Bendahara"),
    ("RSIY-KASIR", "sari.indah", "Sari Indah, A.Md", True, None, "Koordinator Kasir"),
    ("RSIY-KASIR", "wulan.dari", "Wulan Dari", False, None, None),
    # E. Bidang Umum & Kepegawaian
    ("RSIY-BUMUM", "slamet.riyadi", "Drs. Slamet Riyadi, MM", True, None, None),
    ("RSIY-SHUMAS", "anisa.rahma", "Anisa Rahma, S.I.Kom", True, None, None),
    ("RSIY-HUMAS", "fikri.maulana", "Fikri Maulana, S.I.Kom", True, None, "Koordinator Humas & Pemasaran"),
    ("RSIY-PKRS", "desi.ratnasari", "Desi Ratnasari, S.KM", True, None, "Koordinator Promosi Kesehatan RS"),
    ("RSIY-SADM", "sugeng.widodo", "Sugeng Widodo, SE", True, None, None),
    ("RSIY-TU", "lestari.handayani", "Lestari Handayani, A.Md", True, None, "Koordinator Tata Usaha"),
    ("RSIY-TU", "rahayu.ningsih", "Rahayu Ningsih, A.Md", False, Role.ARSIP, "Petugas Arsip"),
    ("RSIY-PELAPORAN", "heru.prasetya", "Heru Prasetya, S.ST", True, None, "Koordinator Pelaporan"),
    ("RSIY-RT", "supardi", "Supardi", True, None, "Koordinator Rumah Tangga"),
    ("RSIY-INVENTORI", "dwi.cahyono", "Dwi Cahyono", True, None, "Koordinator Inventori"),
    ("RSIY-IPSRS", "bagus.wicaksono", "Ir. Bagus Wicaksono", True, None, "Kepala IPSRS"),
    ("RSIY-IPSRS", "rohman", "Rohman", False, None, "Teknisi IPSRS"),
    ("RSIY-SHRD", "erna.wijayanti", "Erna Wijayanti, S.Psi", True, None, None),
    ("RSIY-PERSONALIA", "ratih.kumalasari", "Ratih Kumalasari, SE", True, None, "Koordinator Personalia"),
    ("RSIY-DIKLAT", "galih.pratama", "dr. Galih Pratama", True, None, "Koordinator Diklat"),
    ("RSIY-SKEAMANAN", "sutrisno", "Sutrisno", True, None, None),
    ("RSIY-ANGGOTA", "bayu.saputra", "Bayu Saputra", False, None, "Anggota Satpam"),
    ("RSIY-ANGGOTA", "joko.susilo", "Joko Susilo", False, None, "Anggota Satpam"),
]


def buat_pegawai(password):
    """-> (dibuat, diperbarui). Unit, jabatan, peran, atasan, dan kepala unit diisi dari Master Organisasi."""
    validate_password(password)
    seed_rsiy()
    units = {u.code: u for u in OrganizationUnit.objects.filter(code__startswith="RSIY-")}
    dibuat = diperbarui = 0
    for kode, nama_login, nama, kepala, peran, jabatan in PEGAWAI:
        unit = OrganizationUnit.objects.get(pk=units[kode].pk)      # head terbaru (diisi baris sebelumnya)
        user, baru = User.objects.get_or_create(username=AWALAN + nama_login)
        user.first_name, user.last_name, user.unit, user.is_active = nama, "", unit, True
        user.role = peran or peran_saran(unit, kepala)
        user.position = jabatan or jabatan_saran(unit, kepala)
        user.supervisor = atasan_saran(unit, kepala, user)
        user.set_password(password)
        user.save()
        if kepala and unit.head_id != user.pk:
            unit.head = user
            unit.save(update_fields=["head"])
        dibuat += baru
        diperbarui += not baru
    return dibuat, diperbarui


def nonaktifkan_demo():
    qs = User.objects.filter(username__startswith=AWALAN, is_active=True)
    OrganizationUnit.objects.filter(head__in=qs).update(head=None)
    return qs.update(is_active=False)


# ------------------------------------------------------------------ isian alur
def _pdf(judul):
    """PDF satu halaman berisi judul (berkas contoh yang benar-benar bisa dibuka)."""
    teks = judul.replace("\\", "").replace("(", "[").replace(")", "]")[:90]
    isi = f"BT /F1 14 Tf 60 760 Td (RSI Yatofa - contoh dokumen E-Office) Tj 0 -28 Td ({teks}) Tj ET".encode("latin-1", "replace")
    obj = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
           b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
           b"/Resources << /Font << /F1 5 0 R >> >> >>",
           b"<< /Length %d >>\nstream\n" % len(isi) + isi + b"\nendstream",
           b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, pos = bytearray(b"%PDF-1.4\n"), []
    for i, o in enumerate(obj, 1):
        pos.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(obj) + 1) + b"".join(b"%010d 00000 n \n" % p for p in pos)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(obj) + 1, xref)
    return bytes(out)


def _berkas(nama, judul):
    return SimpleUploadedFile(nama, _pdf(judul), content_type="application/pdf")


def sudah_ada_alur():
    from workflow.models import Task

    return Task.objects.filter(created_by__username__startswith=AWALAN).exists()


@transaction.atomic
def isi_alur(today=None):
    """Isian contoh untuk semua alur. -> ringkasan {jenis: jumlah}. Dilewati bila sudah pernah dibuat."""
    from agenda import services as agenda
    from agenda.models import AgendaEvent
    from arsip import services as arsip
    from arsip.models import ArchiveDocument
    from instructions import services as instruksi
    from instructions.models import InstructionTarget
    from letters import services as surat
    from notifications.services import run_reminders
    from notulen import services as notulen
    from workflow import services as wf
    from workflow.models import Priority, Task, TaskSource

    if sudah_ada_alur():
        return None
    T = today or timezone.localdate()
    hari = lambda n: T + timedelta(days=n)  # noqa: E731
    jam = lambda n, h, m=0: timezone.make_aware(datetime.combine(hari(n), time(h, m)))  # noqa: E731
    p = {u.username[len(AWALAN):]: u for u in User.objects.filter(username__startswith=AWALAN)}
    unit = {u.code[5:]: u for u in OrganizationUnit.objects.filter(code__startswith="RSIY-")}
    dir_, sek, arsiparis = p["ahmad.fauzi"], p["siti.nurhaliza"], p["rahayu.ningsih"]
    n = {"surat masuk": 0, "surat keluar": 0, "disposisi": 0, "instruksi": 0, "penugasan langsung": 0,
         "agenda": 0, "notulen": 0, "arsip manual": 0}

    def jalankan(t, pic, progres=None, status="BERJALAN", hambatan="", keputusan="", bukti=None, kirim=False,
                 periksa=None, setuju=True, catatan_periksa=""):
        """Bawa tugas ke status yang diinginkan lewat langkah yang sama dengan pengguna."""
        t.refresh_from_db()
        if t.instruction_id:
            instruksi.mark_read(t.instruction, pic)         # membuka tugas = instruksi tercatat dibaca
        wf.accept_task(t, pic)
        if progres is not None:
            wf.report_progress(t, pic, progress=progres, status=status, note="Laporan progres.",
                               obstacle=hambatan, decision_needed=keputusan)
        if bukti:
            wf.add_evidence(t, pic, _berkas(bukti[0], bukti[1]), bukti[1])
        if kirim:
            wf.submit_result(t, pic, "Pekerjaan selesai, bukti terlampir.")
            if periksa:
                wf.verify(t, periksa, approved=setuju, note=catatan_periksa)
        return t

    def mundur(t, dibuat, ditutup=None):
        """Tanggal dibuat/ditutup dimundurkan agar dashboard (tren mingguan) tampak seperti data berjalan."""
        f = {"created_at": jam(dibuat, 8)}
        if ditutup is not None:
            f.update(closed_at=jam(ditutup, 15), submitted_at=jam(ditutup, 14))
        Task.objects.filter(pk=t.pk).update(**f)

    # ---------------------------------------------------------------- 1. surat masuk, disposisi, surat keluar
    sm1 = surat.register_incoming(
        sek, letter_number="440/1287/Dinkes/X/2026", letter_date=hari(-6), received_date=hari(-5),
        sender="Dinas Kesehatan Kabupaten", subject="Undangan sosialisasi persiapan akreditasi rumah sakit 2026",
        summary="Sosialisasi standar akreditasi terbaru; RS diminta mengirim tim inti akreditasi.",
        classification="BIASA", attachment=_berkas("undangan-dinkes.pdf", "Undangan sosialisasi akreditasi"))
    sm2 = surat.register_incoming(
        sek, letter_number="1093/KC-XII/1026", letter_date=hari(-14), received_date=hari(-13),
        sender="BPJS Kesehatan Kantor Cabang", subject="Pemberitahuan klaim tertunda pelayanan bulan September 2026",
        summary="37 berkas klaim rawat inap tertunda karena kelengkapan resume medis.",
        classification="TERBATAS", attachment=_berkas("klaim-tertunda-bpjs.pdf", "Klaim tertunda September"))
    sm3 = surat.register_incoming(
        arsiparis, letter_number="PMF/MKT/2026/311", letter_date=hari(-4), received_date=hari(-3),
        sender="PT Medika Farma Nusantara", subject="Penawaran kerja sama pengadaan obat generik 2027",
        summary="Penawaran harga dan skema konsinyasi obat generik.", classification="BIASA",
        attachment=_berkas("penawaran-medika-farma.pdf", "Penawaran kerja sama obat"))
    sm4 = surat.register_incoming(
        sek, letter_number="ADU/2026/019", letter_date=hari(-2), received_date=hari(-2),
        sender="Layanan pengaduan masyarakat", subject="Pengaduan dugaan pelanggaran disiplin petugas",
        summary="Pengaduan keluarga pasien terkait sikap petugas pada shift malam.", classification="RAHASIA",
        attachment=_berkas("pengaduan-019.pdf", "Pengaduan nomor 019"))
    n["surat masuk"] = 4

    d1 = surat.create_disposition(dir_, sm1, to_user=p["budi.santoso"], to_unit=unit["BYAN"],
                                  directive="Siapkan tim inti akreditasi dan hadiri sosialisasi. Laporkan hasilnya.",
                                  priority=Priority.TINGGI, due_date=hari(5), requires_action=True)
    surat.mark_read(d1, p["budi.santoso"])
    d1b = surat.create_disposition(p["budi.santoso"], sm1, parent=d1, to_user=p["indah.permatasari"],
                                   to_unit=unit["MGRPP"], directive="Koordinasikan daftar tim inti per instalasi.",
                                   priority=Priority.TINGGI, due_date=hari(3), requires_action=True)
    jalankan(Task.objects.get(disposition=d1), p["budi.santoso"], 40)
    jalankan(Task.objects.get(disposition=d1b), p["indah.permatasari"], 60)
    d2 = surat.create_disposition(dir_, sm2, to_user=p["rudi.hartono"], to_unit=unit["CASEMIX"],
                                  directive="Lengkapi resume medis 37 klaim dan ajukan ulang sebelum batas BPJS.",
                                  priority=Priority.MENDESAK, due_date=hari(-4), requires_action=True)
    t = jalankan(Task.objects.get(disposition=d2), p["rudi.hartono"], 65,
                 hambatan="12 resume medis belum ditandatangani DPJP.",
                 keputusan="Mohon arahan Direktur kepada DPJP untuk melengkapi tanda tangan.", status="TERHAMBAT")
    mundur(t, -13)
    surat.create_disposition(dir_, sm3, to_user=p["dian.purnamasari"], to_unit=unit["FARMASI"],
                             directive="Untuk diketahui dan dipertimbangkan pada perencanaan 2027.",
                             priority=Priority.RENDAH, requires_action=False)
    surat.create_disposition(dir_, sm4, to_user=p["slamet.riyadi"], to_unit=unit["BUMUM"],
                             directive="Klarifikasi kepada petugas terkait dan laporkan secara tertutup.",
                             priority=Priority.TINGGI, due_date=hari(7), requires_action=True)
    n["disposisi"] = 5

    surat.register_outgoing(sek, letter_date=hari(-3), recipient="Dinas Kesehatan Kabupaten",
                            subject="Konfirmasi kehadiran tim akreditasi RSI Yatofa", classification="BIASA",
                            summary="Tim inti 5 orang dipimpin Kepala Bidang Pelayanan.",
                            attachment=_berkas("konfirmasi-kehadiran.pdf", "Konfirmasi kehadiran"))
    surat.register_outgoing(arsiparis, letter_date=hari(-1), recipient="BPJS Kesehatan Kantor Cabang",
                            subject="Pengajuan ulang klaim tertunda September 2026", classification="TERBATAS",
                            summary="Pengajuan ulang 25 berkas klaim yang telah dilengkapi.",
                            attachment=_berkas("pengajuan-ulang-klaim.pdf", "Pengajuan ulang klaim"))
    n["surat keluar"] = 2

    # ---------------------------------------------------------------- 2. instruksi
    def instruksikan(oleh, targets, terbit=True, **f):
        ins = instruksi.create_instruction(oleh, **f)
        for kode, pic in targets:
            InstructionTarget.objects.create(instruction=ins, unit=unit[kode], pic=p[pic])
        if terbit:
            instruksi.issue(ins, oleh)
        n["instruksi"] += 1
        return ins

    i1 = instruksikan(dir_, [("IGD", "eko.saputra"), ("IRNA", "wahyu.hidayat"), ("IBS", "teguh.prasetyo")],
                      title="Audit kelengkapan troli emergensi seluruh ruang pelayanan",
                      description="Periksa isi, tanggal kedaluwarsa obat, dan fungsi alat pada setiap troli emergensi.",
                      instruction_date=hari(-8), due_date=hari(2), priority=Priority.TINGGI, classification="BIASA",
                      completion_criteria="Checklist troli per ruang + foto, ditandatangani kepala unit.")
    tugas = {x.unit.code[5:]: x for x in Task.objects.filter(instruction=i1).select_related("unit")}
    t = jalankan(tugas["IGD"], p["eko.saputra"], 100, bukti=("checklist-troli-igd.pdf", "Checklist troli IGD"),
                 kirim=True, periksa=dir_)
    mundur(t, -8, -3)
    jalankan(tugas["IRNA"], p["wahyu.hidayat"], 100, bukti=("checklist-troli-irna.pdf", "Checklist troli Rawat Inap"),
             kirim=True)
    jalankan(tugas["IBS"], p["teguh.prasetyo"], 30)

    instruksikan(dir_, [("KMKP", "nurul.hidayah"), ("ETIKMUTU", "yanti.susanti")],
                 title="Penyusunan dokumen akreditasi standar PMKP",
                 description="Susun regulasi, indikator mutu prioritas, dan bukti pelaksanaan standar PMKP.",
                 instruction_date=hari(-2), due_date=hari(14), priority=Priority.SEDANG, classification="BIASA",
                 completion_criteria="Draf dokumen PMKP lengkap untuk direviu Direktur.")
    jalankan(Task.objects.get(instruction__title__startswith="Penyusunan dokumen", pic=p["nurul.hidayah"]),
             p["nurul.hidayah"])

    i3 = instruksikan(sek, [("IPSRS", "bagus.wicaksono")], on_behalf_of=dir_,
                      title="Perbaikan AC ruang rawat inap lantai 2",
                      description="Keluhan pasien: AC kamar 201-206 tidak dingin sejak sepekan.",
                      instruction_date=hari(-12), due_date=hari(-5), priority=Priority.MENDESAK, classification="BIASA",
                      completion_criteria="Suhu ruang 24-26 C, berita acara perbaikan.")
    t = jalankan(Task.objects.get(instruction=i3), p["bagus.wicaksono"], 40, status="TERHAMBAT",
                 hambatan="Kompresor unit kamar 203-204 rusak, suku cadang belum tersedia.",
                 keputusan="Persetujuan pembelian kompresor baru Rp 18.500.000.")
    mundur(t, -12)

    instruksikan(dir_, [("DIKLAT", "galih.pratama")], terbit=False,
                 title="Rencana pelatihan Bantuan Hidup Dasar untuk seluruh perawat",
                 description="Jadwal bertahap per ruang, target 100% perawat tersertifikasi BHD.",
                 instruction_date=T, due_date=hari(30), priority=Priority.SEDANG, classification="BIASA")

    i5 = instruksikan(p["hendro.kusumo"], [("KASIR", "sari.indah"), ("AKUNTANSI", "taufik.hidayat")],
                      title="Rekonsiliasi kas dan piutang pasien bulan Oktober 2026",
                      description="Cocokkan setoran kasir, rekening koran, dan piutang BPJS/asuransi.",
                      instruction_date=hari(-5), due_date=hari(1), priority=Priority.TINGGI, classification="TERBATAS",
                      completion_criteria="Berita acara rekonsiliasi ditandatangani Kabid Keuangan.")
    jalankan(Task.objects.get(instruction=i5, pic=p["sari.indah"]), p["sari.indah"], 70)
    jalankan(Task.objects.get(instruction=i5, pic=p["taufik.hidayat"]), p["taufik.hidayat"], 100,
             bukti=("rekonsiliasi-oktober.pdf", "Rekonsiliasi Oktober"), kirim=True,
             periksa=p["hendro.kusumo"], setuju=False,
             catatan_periksa="Selisih piutang asuransi Rp 2,3 juta belum dijelaskan. Lengkapi rinciannya.")

    # ---------------------------------------------------------------- 3. penugasan langsung
    def tugaskan(oleh, pic, kode, mulai, **f):
        n["penugasan langsung"] += 1
        t = wf.create_task(created_by=oleh, source_type=TaskSource.LANGSUNG, unit=unit[kode], pic=p[pic],
                           start_date=hari(mulai), classification="BIASA", **f)
        mundur(t, mulai)
        return t

    t = tugaskan(p["eko.saputra"], "fajar.nugroho", "IGD", -4, title="Rekap kunjungan dan waktu tanggap IGD Oktober",
                 source_note="Bahan rapat evaluasi bulanan pelayanan", due_date=hari(2), priority=Priority.SEDANG,
                 completion_criteria="Tabel kunjungan harian + rata-rata waktu tanggap.",
                 collaborators=[p["lina.marlina"]])
    jalankan(t, p["fajar.nugroho"], 50)
    tugaskan(p["dian.purnamasari"], "rahmat.hidayat", "FARMASI", -14, title="Stock opname obat high alert",
             source_note="Temuan ronde keselamatan pasien", due_date=hari(-6), priority=Priority.TINGGI,
             completion_criteria="Berita acara stock opname dan daftar selisih.")
    t = tugaskan(p["herlina"], "andi.setiawan", "LAB", -20, title="Kalibrasi alat hematology analyzer",
                 source_note="Jadwal kalibrasi tahunan", due_date=hari(-9), priority=Priority.SEDANG,
                 completion_criteria="Sertifikat kalibrasi dari vendor.")
    jalankan(t, p["andi.setiawan"], 100, bukti=("sertifikat-kalibrasi.pdf", "Sertifikat kalibrasi"), kirim=True,
             periksa=p["herlina"])
    mundur(t, -20, -10)
    t = tugaskan(p["ratna.dewi"], "yuliana", "GIZI", -6, title="Evaluasi menu diet pasien diabetes melitus",
                 source_note="Masukan Komite Medik", due_date=hari(10), priority=Priority.RENDAH)
    wf.cancel(t, p["ratna.dewi"], "Digabung ke program evaluasi menu terapi diet 2027.")
    t = tugaskan(p["slamet.riyadi"], "erna.wijayanti", "SHRD", -10, title="Rekap kebutuhan diklat pegawai 2027",
                 source_note="Penyusunan RKA 2027", due_date=hari(4), priority=Priority.SEDANG,
                 completion_criteria="Rekap kebutuhan per unit dan perkiraan biaya.")
    jalankan(t, p["erna.wijayanti"], 100, bukti=("kebutuhan-diklat-2027.pdf", "Kebutuhan diklat 2027"), kirim=True)
    t = tugaskan(p["dian.purnamasari"], "nita.anggraini", "FARMASI", -25, title="Penataan ulang gudang farmasi",
                 source_note="Hasil audit internal SPI", due_date=hari(-16), priority=Priority.SEDANG,
                 completion_criteria="Denah dan foto penataan.")
    jalankan(t, p["nita.anggraini"], 100, bukti=("penataan-gudang.pdf", "Penataan gudang"), kirim=True,
             periksa=p["dian.purnamasari"])
    mundur(t, -25, -17)
    t = tugaskan(p["sugeng.widodo"], "supardi", "RT", -18, title="Pengecatan ulang koridor rawat jalan",
                 source_note="Persiapan akreditasi", due_date=hari(-11), priority=Priority.RENDAH)
    jalankan(t, p["supardi"], 100, bukti=("koridor-selesai.pdf", "Foto koridor"), kirim=True, periksa=p["sugeng.widodo"])
    mundur(t, -18, -12)

    # ---------------------------------------------------------------- 4. agenda, notulen, tindak lanjut
    pimpinan = [p[x] for x in ("budi.santoso", "hendro.kusumo", "slamet.riyadi", "indah.permatasari",
                               "nurul.hidayah", "siti.nurhaliza")]
    r1 = agenda.create_event(dir_, participants=pimpinan + [p["eko.saputra"], p["wahyu.hidayat"],
                                                             p["dian.purnamasari"]],
                             title="Rapat koordinasi mutu dan keselamatan pasien Oktober", kind=AgendaEvent.Kind.RAPAT,
                             start=jam(-7, 9), end=jam(-7, 11), location="Ruang rapat Direksi lt. 2",
                             notes="1. Capaian indikator mutu nasional\n2. Insiden keselamatan pasien\n3. Antrean farmasi",
                             classification="BIASA")
    m1 = notulen.create_minutes(sek, r1, attendees=[dir_] + pimpinan[:5] + [p["eko.saputra"], p["dian.purnamasari"]],
                                discussion="Capaian kepatuhan cuci tangan 92%. Waktu tunggu obat rawat jalan rata-rata "
                                           "58 menit (standar 30 menit). Dua insiden KNC dilaporkan IGD.",
                                summary="Fokus perbaikan: waktu tunggu farmasi dan pelaporan indikator mutu tepat waktu.")
    k1 = notulen.add_decision(m1, sek, text="Setiap instalasi melaporkan indikator mutu nasional paling lambat tanggal 5 "
                                            "setiap bulan.", requires_action=True, priority=Priority.SEDANG,
                              due_date=hari(6), completion_criteria="Laporan indikator mutu Oktober.")
    notulen.add_assignee(k1, sek, unit["IGD"], p["eko.saputra"])
    notulen.add_assignee(k1, sek, unit["IRNA"], p["wahyu.hidayat"])
    k2 = notulen.add_decision(m1, sek, text="Perbaikan alur antrean farmasi rawat jalan dengan target waktu tunggu "
                                            "di bawah 30 menit.", requires_action=True, priority=Priority.TINGGI,
                              due_date=hari(1), completion_criteria="SOP alur baru dan data waktu tunggu 1 minggu.")
    notulen.add_assignee(k2, sek, unit["FARMASI"], p["dian.purnamasari"])
    notulen.add_decision(m1, sek, text="Direktur mengapresiasi capaian kepatuhan cuci tangan 92%.",
                         requires_action=False)
    notulen.submit(m1, sek)
    notulen.approve(m1, dir_)
    jalankan(Task.objects.get(decision=k1, pic=p["eko.saputra"]), p["eko.saputra"], 80)
    jalankan(Task.objects.get(decision=k2), p["dian.purnamasari"], 45)

    r2 = agenda.create_event(p["hendro.kusumo"], participants=[p["rudi.hartono"], p["taufik.hidayat"],
                                                               p["indah.permatasari"]],
                             title="Rapat evaluasi klaim BPJS triwulan III", kind=AgendaEvent.Kind.RAPAT,
                             start=jam(-3, 13), end=jam(-3, 15), location="Ruang rapat Keuangan", classification="TERBATAS")
    m2 = notulen.create_minutes(p["rudi.hartono"], r2, attendees=[p["rudi.hartono"], p["taufik.hidayat"]],
                                discussion="Rasio klaim tertunda naik menjadi 6,1%. Penyebab utama: resume medis tidak lengkap.",
                                summary="Perlu verifikasi internal sebelum klaim dikirim.")
    k = notulen.add_decision(m2, p["rudi.hartono"], text="Casemix melakukan verifikasi internal seluruh berkas klaim "
                                                          "sebelum dikirim ke BPJS.", requires_action=True,
                             priority=Priority.TINGGI, due_date=hari(10))
    notulen.add_assignee(k, p["rudi.hartono"], unit["CASEMIX"], p["rudi.hartono"])
    notulen.submit(m2, p["rudi.hartono"])                      # menunggu persetujuan Kabid Keuangan

    r3 = agenda.create_event(p["budi.santoso"], participants=[p["indah.permatasari"], p["arif.rahman"],
                                                              p["ratna.dewi"], p["kartini"], p["nurul.hidayah"]],
                             title="Rapat persiapan akreditasi: pembagian Pokja", kind=AgendaEvent.Kind.RAPAT,
                             start=jam(2, 10), end=jam(2, 12), location="Aula RSI Yatofa", classification="BIASA",
                             notes="Pembagian kelompok kerja dan jadwal telusur dokumen.")
    agenda.add_material(r3, p["budi.santoso"], _berkas("bahan-pokja-akreditasi.pdf", "Bahan rapat Pokja"),
                        "Daftar standar dan usulan Pokja")
    agenda.create_event(sek, participants=[p["budi.santoso"], p["indah.permatasari"], p["wahyu.hidayat"]],
                        organizer=dir_, title="Visite manajemen ke ruang rawat inap", kind=AgendaEvent.Kind.KEGIATAN,
                        start=jam(0, 13), end=jam(0, 14), location="Instalasi Rawat Inap", classification="BIASA")
    agenda.create_event(sek, participants=[p["budi.santoso"], p["slamet.riyadi"]], organizer=dir_,
                        title="Kunjungan Dinas Kesehatan: monitoring pelayanan", kind=AgendaEvent.Kind.KUNJUNGAN,
                        start=jam(5, 9), end=jam(5, 11), location="Lobi utama", classification="BIASA")
    batal = agenda.create_event(p["slamet.riyadi"], participants=[p["muhammad.iqbal"], p["dimas.aditya"]],
                                title="Rapat vendor pengembangan SIMRS", kind=AgendaEvent.Kind.RAPAT,
                                start=jam(1, 14), end=jam(1, 15), location="Ruang IT", classification="BIASA")
    agenda.cancel_event(batal, p["slamet.riyadi"], "Vendor meminta penjadwalan ulang pekan depan.")
    n["agenda"], n["notulen"] = 6, 2

    # ---------------------------------------------------------------- 5. arsip manual + usulan pemusnahan
    arsip.create_manual(arsiparis, _berkas("sk-tim-akreditasi-2026.pdf", "SK Tim Akreditasi 2026"),
                        doc_type=ArchiveDocument.DocType.LAINNYA, number="SK/DIR/045/X/2026", doc_date=hari(-9),
                        title="SK Direktur tentang Tim Akreditasi RSI Yatofa 2026", unit=unit["DIR"],
                        classification="BIASA", keywords="akreditasi, SK, tim")
    lama = arsip.create_manual(arsiparis, _berkas("laporan-kegiatan-2019.pdf", "Laporan kegiatan 2019"),
                               doc_type=ArchiveDocument.DocType.LAPORAN, number="LAP/TU/2019/12",
                               doc_date=T.replace(year=T.year - 7), title="Laporan kegiatan tahunan Tata Usaha 2019",
                               unit=unit["TU"], classification="BIASA", keywords="laporan tahunan")
    arsip.propose_disposal(lama, arsiparis, "Masa retensi 5 tahun berakhir; isi sudah tercakup laporan tahunan RS.",
                           today=T)
    n["arsip manual"] = 2

    # ---------------------------------------------------------------- 6. pengingat & eskalasi hari ini
    run_reminders(T)
    return n
