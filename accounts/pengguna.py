"""Master Pengguna: input pegawai per unit/bidang berdasarkan Master Organisasi.

Unit dipilih dari pohon organisasi; jabatan, peran, dan atasan langsung DISARANKAN dari struktur (bisa diubah):
- kepala unit  -> jabatan = nama unit ("Kepala Seksi ...", atau "Kepala Instalasi ..."), atasan = kepala unit induk
- staf         -> jabatan = "Staf <unit>", atasan = kepala unit sendiri (atau kepala induk terdekat bila kosong)
Pengguna tidak pernah dihapus: dinonaktifkan agar riwayat tugas/surat tetap utuh.
"""
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from audit import services as audit

from .models import OrganizationUnit, Role, User
from .organisasi import can_manage

K = OrganizationUnit.Kind
_PERAN_KEPALA = {K.DIREKSI: Role.DIREKTUR, K.BIDANG: Role.WADIR, K.MANAJER: Role.WADIR}
_AWALAN_JABATAN = ("Kepala", "Direktur", "Manager", "Manajer", "Komisaris", "Ketua")


def jabatan_saran(unit, kepala):
    if unit is None:
        return ""
    if not kepala:
        return f"Staf {unit.name}"
    if unit.name.startswith(_AWALAN_JABATAN):
        return unit.name
    if unit.kind == K.KOMITE:
        return f"Ketua {unit.name}"
    return f"Kepala {unit.name}"


def peran_saran(unit, kepala):
    if unit is None or not kepala:
        return Role.STAF
    return _PERAN_KEPALA.get(unit.kind, Role.KEPALA_UNIT)


def atasan_saran(unit, kepala, pengguna=None):
    """Kepala aktif terdekat di garis struktural (unit sendiri bila staf, mulai induk bila kepala)."""
    u, lihat = (unit.parent if kepala else unit) if unit else None, set()
    while u and u.pk not in lihat:
        lihat.add(u.pk)
        h = u.head
        if h and h.is_active and (pengguna is None or h.pk != pengguna.pk):
            return h
        u = u.parent
    return None


def pilihan_unit(sertakan=None):
    """[(pk, label bertingkat)] urut pohon; unit aktif + `sertakan` (unit lama pengguna meski nonaktif)."""
    qs = OrganizationUnit.objects.order_by("order", "name")
    units = [u for u in qs if u.is_active or (sertakan and u.pk == sertakan.pk)]
    ada = {u.pk for u in units}
    per_induk = {}
    for u in units:
        per_induk.setdefault(u.parent_id if u.parent_id in ada else None, []).append(u)
    out = []

    def jalan(induk, depth):
        for u in per_induk.get(induk, []):
            out.append((u, depth))
            jalan(u.pk, depth + 1)
    jalan(None, 0)
    return out


def peta_saran(pilihan):
    """Data untuk isian otomatis di form (dibaca app.js): {pk: {kepala:{jabatan,peran,atasan}, staf:{...}}}."""
    def satu(u, kepala):
        a = atasan_saran(u, kepala)
        return {"jabatan": jabatan_saran(u, kepala), "peran": peran_saran(u, kepala),
                "atasan": a.pk if a else "", "atasan_nama": str(a) if a else ""}
    return {str(u.pk): {"kepala": satu(u, True), "staf": satu(u, False),
                        "kepala_kini": str(u.head) if u.head_id else ""} for u, _ in pilihan}


def _cek(admin, target=None):
    if not can_manage(admin):
        raise PermissionDenied
    if target is not None and target.is_superuser and not admin.is_superuser:
        raise PermissionDenied("Akun superuser hanya dapat diubah oleh superuser.")


def _lengkapi(user, kepala):
    """Isi jabatan/atasan kosong dari struktur."""
    if user.unit_id and not user.position:
        user.position = jabatan_saran(user.unit, kepala)
    if user.unit_id and not user.supervisor_id:
        user.supervisor = atasan_saran(user.unit, kepala, user)
    if user.supervisor_id and user.supervisor_id == user.pk:
        raise ValidationError({"supervisor": "Atasan langsung tidak boleh diri sendiri."})


def _set_kepala(admin, user, kepala, unit_lama):
    """Sinkronkan OrganizationUnit.head. -> nama kepala lama yang digantikan (untuk pesan) atau None."""
    diganti = None
    if unit_lama and unit_lama.pk != user.unit_id and unit_lama.head_id == user.pk:
        unit_lama.head = None
        unit_lama.save(update_fields=["head"])
        audit.log(admin, "org.head", unit_lama, head=(str(user), None))
    if not user.unit_id:
        return None
    unit = OrganizationUnit.objects.select_for_update().get(pk=user.unit_id)
    if kepala and unit.head_id != user.pk:
        lama = unit.head
        diganti = str(lama) if lama else None
        unit.head = user
        unit.save(update_fields=["head"])
        audit.log(admin, "org.head", unit, head=(diganti, str(user)))
    elif not kepala and unit.head_id == user.pk:
        unit.head = None
        unit.save(update_fields=["head"])
        audit.log(admin, "org.head", unit, head=(str(user), None))
    return diganti


@transaction.atomic
def create_user(admin, data, password, kepala=False):
    _cek(admin)
    user = User(**data)
    validate_password(password, user)
    _lengkapi(user, kepala)
    user.set_password(password)
    user.full_clean(exclude=["password"])
    user.save()
    diganti = _set_kepala(admin, user, kepala, None)
    audit.log(admin, "user.create", user, unit=user.unit, role=user.role, position=user.position,
              supervisor=user.supervisor, kepala=kepala)
    return user, diganti


@transaction.atomic
def update_user(admin, user, data, password="", kepala=False):
    _cek(admin, user)
    user = User.objects.select_for_update().get(pk=user.pk)
    unit_lama = user.unit
    lama = {k: getattr(user, k) for k in data}
    for k, v in data.items():
        setattr(user, k, v)
    if password:
        validate_password(password, user)
        user.set_password(password)
    _lengkapi(user, kepala)
    user.full_clean(exclude=["password"])
    user.save()
    diganti = _set_kepala(admin, user, kepala, unit_lama)
    berubah = {k: (lama[k], getattr(user, k)) for k in data if lama[k] != getattr(user, k)}
    if password:
        berubah["password"] = "diganti"
    if berubah:
        audit.log(admin, "user.update", user, **berubah)
    return user, diganti


@transaction.atomic
def deactivate(admin, user):
    _cek(admin, user)
    if user.pk == admin.pk:
        raise ValidationError("Anda tidak dapat menonaktifkan akun sendiri.")
    user.is_active = False
    user.save(update_fields=["is_active"])
    dilepas = list(user.headed_units.values_list("name", flat=True))
    user.headed_units.update(head=None)          # kepala nonaktif tidak boleh menerima eskalasi
    audit.log(admin, "user.deactivate", user, kepala_dilepas=dilepas)
    return dilepas


@transaction.atomic
def activate(admin, user):
    _cek(admin, user)
    user.is_active = True
    user.save(update_fields=["is_active"])
    audit.log(admin, "user.activate", user)
