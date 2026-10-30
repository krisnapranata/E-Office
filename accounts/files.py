"""Validasi dan penyimpanan unggahan terproteksi."""
import os
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import Http404


def validate_upload(f):
    ext = os.path.splitext(f.name)[1].lower().lstrip(".")
    if ext not in settings.UPLOAD_ALLOWED_EXTENSIONS:
        raise ValidationError(
            "Jenis berkas tidak diizinkan. Gunakan: "
            + ", ".join(settings.UPLOAD_ALLOWED_EXTENSIONS)
        )
    if f.size > settings.UPLOAD_MAX_BYTES:
        raise ValidationError(
            f"Ukuran berkas melebihi {settings.UPLOAD_MAX_BYTES // (1024 * 1024)} MB."
        )


def protected_upload_to(prefix):
    """Nama berkas acak agar URL/nama asli tidak dapat ditebak."""

    def _upload_to(instance, filename):
        ext = os.path.splitext(filename)[1].lower()
        return f"{prefix}/{uuid.uuid4().hex}{ext}"

    _upload_to.__qualname__ = f"protected_upload_to_{prefix}"
    return _upload_to


def evidence_upload_to(instance, filename):
    return protected_upload_to("bukti")(instance, filename)


def letter_upload_to(instance, filename):
    return protected_upload_to("surat")(instance, filename)


def instruction_upload_to(instance, filename):
    return protected_upload_to("instruksi")(instance, filename)


def buka_berkas(fieldfile):
    """Buka berkas unggahan untuk diunduh; berkas yang hilang dari penyimpanan = 404, bukan galat server."""
    try:
        return fieldfile.open("rb")
    except FileNotFoundError:
        raise Http404("Berkas tidak ditemukan di penyimpanan.")


# Berkas yang boleh DITAMPILKAN di browser (bukan diunduh). Hanya PDF dan gambar raster: Word/Excel tidak bisa
# ditampilkan browser, dan tipe lain (HTML/SVG) bisa menjalankan skrip. Content-Type ditetapkan dari ekstensi dan
# SecurityMiddleware mengirim X-Content-Type-Options: nosniff, sehingga berkas palsu (mis. HTML berekstensi .pdf)
# tidak pernah dibaca sebagai HTML.
TIPE_PRATINJAU = {"pdf": "application/pdf", "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}


def bisa_dilihat(nama):
    return os.path.splitext(nama or "")[1].lower().lstrip(".") in TIPE_PRATINJAU


def respons_berkas(request, fieldfile, nama):
    """FileResponse unduhan; `?lihat=1` pada PDF/gambar = tampil di browser (boleh di-iframe dari halaman sendiri).
    -> (response, dilihat) — `dilihat` dipakai untuk mencatat audit (lihat vs unduh)."""
    from django.http import FileResponse

    lihat = request.GET.get("lihat") == "1" and bisa_dilihat(nama)
    if not lihat:
        return FileResponse(buka_berkas(fieldfile), as_attachment=True, filename=nama), False
    ext = os.path.splitext(nama)[1].lower().lstrip(".")
    r = FileResponse(buka_berkas(fieldfile), as_attachment=False, filename=nama, content_type=TIPE_PRATINJAU[ext])
    r["X-Frame-Options"] = "SAMEORIGIN"           # bawaan proyek DENY; pratinjau ditanam di halaman detail sendiri
    r["Cache-Control"] = "private, no-store"
    return r, True
