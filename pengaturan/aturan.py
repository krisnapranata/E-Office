"""Aturan "tugas hanya ke bawahan" (Pengaturan Aplikasi → Aturan penugasan).

Bila aktif, Wakil Direktur dan Kepala Unit hanya dapat menunjuk penerima di unit sendiri dan sub-unitnya untuk:
penugasan langsung (PIC), ubah penanggung jawab (PIC baru), disposisi termasuk terusan (penerima & unit), dan
penerima instruksi (pemberi instruksi = pihak "atas nama" bila dicatat sekretaris).
Tidak dibatasi: Direktur (boleh ke siapa saja), kolaborator (kerja lintas unit), PIC keputusan rapat (rapat lintas unit).
Formulir memakai `saring_*` (pilihan disaring); service memakai `cek_*` (server menolak walau formulir dipaksa).
"""
from django.core.exceptions import ValidationError

from accounts.models import Role
from accounts.permissions import managed_unit_ids

PERAN_TERBATAS = {Role.WADIR, Role.KEPALA_UNIT}
PESAN = "Aturan \"tugas hanya ke bawahan\" aktif: pilih {apa} di unit Anda atau sub-unitnya."


def aktif():
    from .models import PengaturanAplikasi

    return PengaturanAplikasi.ambil().tugas_hanya_ke_bawah


def lingkup(pemberi):
    """Unit yang boleh dituju pemberi ini, atau None bila tidak dibatasi."""
    if pemberi is None or pemberi.is_superuser or pemberi.role not in PERAN_TERBATAS or not aktif():
        return None
    return managed_unit_ids(pemberi)


def saring_pengguna(pemberi, qs):
    unit = lingkup(pemberi)
    return qs if unit is None else qs.filter(unit_id__in=unit)


def saring_unit(pemberi, qs):
    unit = lingkup(pemberi)
    return qs if unit is None else qs.filter(pk__in=unit)


def saring_field(field, pemberi, jenis="pengguna"):
    """Saring pilihan formulir; pilihan di luar lingkup ditolak dengan pesan yang menyebut aturan ini."""
    if lingkup(pemberi) is None:
        return
    field.queryset = (saring_unit if jenis == "unit" else saring_pengguna)(pemberi, field.queryset)
    field.error_messages["invalid_choice"] = PESAN.format(apa="unit" if jenis == "unit" else "penerima")
    field.help_text = "Hanya unit Anda dan sub-unitnya (aturan \"tugas hanya ke bawahan\" aktif)."


def cek_penerima(pemberi, *, pengguna=None, unit=None, field_pengguna="pic", field_unit="unit"):
    """ValidationError bila penerima (pengguna dan/atau unit) di luar lingkup pemberi."""
    boleh = lingkup(pemberi)
    if boleh is None:
        return
    galat = {}
    if pengguna is not None and pengguna.unit_id not in boleh:
        galat[field_pengguna] = PESAN.format(apa="penerima")
    if unit is not None and unit.pk not in boleh:
        galat[field_unit] = PESAN.format(apa="unit")
    if galat:
        raise ValidationError(galat)
