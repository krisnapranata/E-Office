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
