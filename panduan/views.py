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
        "modul": [{"no": m["no"], "nama": m["nama"], "ikon": m["ikon"], "url": reverse(m["url"]),
                   "fungsi": m["fungsi"], "siapa": _isi(m["siapa"], nilai),
                   "aturan": [_isi(x, nilai) for x in m["aturan"]],
                   "tugas": [_tugas(t, nilai) for t in m["tugas"]]} for m in konten.MODUL],
        "aturan": nilai,
    }


@login_required
def index(request):
    return render(request, "panduan/index.html", bangun(request.user))
