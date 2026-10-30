from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import NoReverseMatch, reverse

from accounts.models import Role

from . import konten


def _konteks_aturan():
    """Nilai yang dapat dikonfigurasi, dibaca saat halaman dibuka (panduan = perilaku sistem)."""
    cfg = settings.EOFFICE
    label = dict(Role.choices)
    return {
        "jam_pengingat": f"{cfg.get('REMINDER_HOUR', 7):02d}",
        "hari_pengingat": " dan ".join(f"H-{d}" for d in cfg["REMINDER_DAYS_BEFORE"]) or "tidak ada",
        "hari_eskalasi": cfg["ESCALATION_DAYS_OVERDUE"],
        "jenis_berkas": ", ".join(e.upper() for e in settings.UPLOAD_ALLOWED_EXTENSIONS),
        "ukuran_berkas": settings.UPLOAD_MAX_BYTES // (1024 * 1024),
        "penerbit_instruksi": ", ".join(label.get(r, r) for r in cfg["INSTRUCTION_ISSUER_ROLES"]),
        "hari_agenda": " dan ".join("hari-H" if d == 0 else f"H-{d}" for d in cfg.get("AGENDA_REMINDER_DAYS", [1, 0])),
        "tahun_retensi": cfg.get("RETENTION_YEARS", {}).get("DEFAULT", 5),
    }


# Urutan kolom matriks = urutan organisasi
PERAN_MATRIKS = [Role.DIREKTUR, Role.WADIR, Role.KEPALA_UNIT, Role.STAF, Role.SEKRETARIS, Role.ARSIP, Role.AUDITOR,
                 Role.ADMIN]


def _matriks_wewenang():
    """Tindakan × peran, dihitung dari fungsi izin yang DIPAKAI sistem -> panduan tidak bisa berbeda dari perilaku.
    Sel: (tanda, keterangan) dengan tanda 'ya' / 'syarat' / 'tidak'."""
    from accounts.models import User
    from accounts.permissions import (EXECUTIVE_ROLES, can_assign_task, can_dispose, can_issue_instruction,
                                      can_register_letter)
    from agenda.services import can_create_event

    def u(r):
        return User(role=r)

    pimpinan = {Role.WADIR, Role.KEPALA_UNIT}
    baris = []

    def tambah(tindakan, fn):
        baris.append((tindakan, [fn(r) for r in PERAN_MATRIKS]))

    tambah("Memberi penugasan langsung", lambda r: ("ya", "") if can_assign_task(u(r)) else ("tidak", ""))
    tambah("Menerbitkan instruksi", lambda r: (
        ("syarat", "atas nama pimpinan") if r == Role.SEKRETARIS else ("ya", "")) if can_issue_instruction(u(r))
        else ("tidak", ""))
    tambah("Mencatat surat masuk/keluar", lambda r: ("ya", "") if can_register_letter(u(r)) else ("tidak", ""))
    tambah("Membuat disposisi", lambda r: ("ya", "") if can_dispose(u(r)) else ("tidak", ""))
    tambah("Meneruskan disposisi", lambda r: ("syarat", "bila ia penerimanya") if can_dispose(u(r)) else ("tidak", ""))
    tambah("Membuat agenda/rapat", lambda r: ("ya", "") if can_create_event(u(r)) else ("tidak", ""))
    tambah("Menyetujui notulen", lambda r: ("syarat", "bila pimpinan rapat") if can_create_event(u(r)) else ("tidak", ""))
    tambah("Mengerjakan tugas (PIC)", lambda r: ("tidak", "hanya baca") if r == Role.AUDITOR else ("syarat", "bila ditunjuk"))
    tambah("Memeriksa & menutup tugas", lambda r: (
        ("syarat", "tugas yang diberikannya") if can_assign_task(u(r)) or can_dispose(u(r))
        or (can_issue_instruction(u(r)) and r != Role.SEKRETARIS) else ("tidak", "")))
    tambah("Minta kabar, beri arahan, ubah PIC/tenggat, batalkan", lambda r: (
        ("ya", "semua tugas") if r == Role.DIREKTUR else
        ("syarat", "tugas yang diberikannya + tugas di unit & sub-unitnya") if r in pimpinan else
        ("tidak", "hanya baca") if r == Role.AUDITOR else ("tidak", "")))
    tambah("Melihat tugas", lambda r: (
        ("ya", "semua, termasuk Rahasia") if r == Role.DIREKTUR else
        ("syarat", "semua kecuali Rahasia") if r in EXECUTIVE_ROLES else
        ("syarat", "unit & sub-unitnya + yang ia terlibat") if r in pimpinan else
        ("syarat", "yang ia terlibat")))
    tambah("Memutuskan pemusnahan arsip", lambda r: (
        ("ya", "") if r == Role.DIREKTUR else ("syarat", "mengusulkan") if r == Role.ARSIP else ("tidak", "")))
    label = dict(Role.choices)
    return {"kolom": [label[r] for r in PERAN_MATRIKS], "baris": baris}


def _isi(teks, nilai):
    return teks.format(**nilai)


def _tugas(t, nilai):
    try:
        url = reverse(t["url"]) if t["url"] else ""
    except NoReverseMatch:
        url = ""
    return {"judul": t["judul"], "url": url, "langkah": [_isi(x, nilai) for x in t["langkah"]]}


def bangun(user):
    """Struktur halaman: peran pengguna lebih dulu, lalu peran lain sesuai urutan organisasi."""
    nilai = _konteks_aturan()
    label = dict(Role.choices)
    peran = []
    for p in konten.PERAN:
        peran.append({
            "kode": p["kode"], "nama": label[p["kode"]], "ikon": p["ikon"], "ringkas": p["ringkas"],
            "lingkup": p["lingkup"], "tidak": p["tidak"], "milik_saya": p["kode"] == user.role,
            "tugas": [_tugas(t, nilai) for t in p["tugas"]],
        })
    peran.sort(key=lambda p: not p["milik_saya"])
    return {
        "alur": [(ikon, judul, _isi(teks, nilai)) for ikon, judul, teks in konten.ALUR],
        "status": konten.STATUS,
        "penanda": konten.PENANDA,
        "peran": peran,
        "faq": [(q, _isi(a, nilai)) for q, a in konten.FAQ],
        "alur_tugas": {
            "ringkas": konten.ALUR_TUGAS_RINGKAS,
            "hirarki": konten.HIRARKI,
            "samping": [(i, j, _isi(t, nilai)) for i, j, t in konten.HIRARKI_SAMPING],
            "jalur": [(i, n, _isi(m, nilai), k, p, v, c) for i, n, m, k, p, v, c in konten.JALUR_TUGAS],
            "pantau": [(p, _isi(a, nilai), b, _isi(c, nilai)) for p, a, b, c in konten.PANTAU_TUGAS],
            "contoh": [(siapa, _isi(t, nilai)) for siapa, t in konten.CONTOH_ALUR],
            "catatan": konten.CATATAN_ALUR,
            "matriks": _matriks_wewenang(),
        },
        "modul": [{"no": m["no"], "nama": m["nama"], "ikon": m["ikon"], "url": reverse(m["url"]),
                   "fungsi": m["fungsi"], "siapa": _isi(m["siapa"], nilai),
                   "aturan": [_isi(x, nilai) for x in m["aturan"]],
                   "tugas": [_tugas(t, nilai) for t in m["tugas"]]} for m in konten.MODUL],
        "aturan": nilai,
    }


@login_required
def index(request):
    return render(request, "panduan/index.html", bangun(request.user))
