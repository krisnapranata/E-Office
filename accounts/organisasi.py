"""Master Organisasi: pohon unit struktural + hubungan koordinasi/pengawasan.

- Hierarki STRUKTURAL = `OrganizationUnit.parent` (dipakai lingkup akses atasan & eskalasi).
- Hubungan NON-struktural = `OrganizationRelation` (komite/SPI ke Direktur); tidak memengaruhi akses.
- Tidak ada penghapusan unit: unit dinonaktifkan (data lama yang merujuk unit tetap utuh).
"""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count

from audit import services as audit

from .models import OrganizationRelation, OrganizationUnit, Role, User


def can_manage(user):
    """Pengelola master organisasi: Administrator Sistem (peran) atau superuser."""
    return user.is_authenticated and (user.role == Role.ADMIN or user.is_superuser)


def would_cycle(unit, parent):
    """True bila menjadikan `parent` induk `unit` membuat hubungan melingkar."""
    if parent is None:
        return False
    if unit.pk is None:
        return False
    return parent.pk in unit.descendant_ids()


def tree(include_inactive=False):
    """Daftar akar beserta anak bertingkat: [{"unit", "children": [...]}], urut (order, nama)."""
    qs = OrganizationUnit.objects.select_related("head").order_by("order", "name")
    if not include_inactive:
        qs = qs.filter(is_active=True)
    units = list(qs)
    per_induk = {}
    for u in units:
        per_induk.setdefault(u.parent_id, []).append(u)
    ada = {u.pk for u in units}
    relasi = {}
    for r in OrganizationRelation.objects.select_related("target").filter(unit_id__in=ada):
        relasi.setdefault(r.unit_id, []).append(r)
    anggota = dict(
        User.objects.filter(is_active=True, unit_id__in=ada).values("unit_id").annotate(n=Count("pk"))
        .values_list("unit_id", "n"))

    def simpul(u, depth):
        return {"unit": u, "depth": depth, "relations": relasi.get(u.pk, []), "members": anggota.get(u.pk, 0),
                "children": [simpul(c, depth + 1) for c in per_induk.get(u.pk, [])]}

    # akar = tanpa induk, atau induknya disembunyikan (nonaktif)
    akar = [u for u in units if u.parent_id is None or u.parent_id not in ada]
    return [simpul(u, 0) for u in akar]


def _validate(unit, parent):
    if parent and parent.pk == unit.pk:
        raise ValidationError({"parent": "Unit tidak boleh menjadi induk dirinya sendiri."})
    if would_cycle(unit, parent):
        raise ValidationError({"parent": "Induk tidak boleh salah satu sub-unit dari unit ini (hubungan melingkar)."})
    if parent and not parent.is_active:
        raise ValidationError({"parent": "Induk harus unit yang aktif."})


@transaction.atomic
def create_unit(user, **fields):
    if not can_manage(user):
        raise PermissionDenied
    unit = OrganizationUnit(**fields)
    _validate(unit, unit.parent)
    unit.full_clean()
    unit.save()
    audit.log(user, "org.create", unit, parent=unit.parent, kind=unit.kind)
    return unit


@transaction.atomic
def update_unit(unit, user, **fields):
    if not can_manage(user):
        raise PermissionDenied
    unit = OrganizationUnit.objects.select_for_update().get(pk=unit.pk)
    _validate(unit, fields.get("parent", unit.parent))
    lama = {k: getattr(unit, k) for k in fields}
    for k, v in fields.items():
        setattr(unit, k, v)
    unit.full_clean()
    unit.save()
    berubah = {k: (lama[k], v) for k, v in fields.items() if lama[k] != v}
    if berubah:
        audit.log(user, "org.update", unit, **berubah)
    return unit


@transaction.atomic
def deactivate(unit, user, reason):
    if not can_manage(user):
        raise PermissionDenied
    if not reason.strip():
        raise ValidationError({"reason": "Alasan penonaktifan wajib diisi."})
    aktif = unit.children.filter(is_active=True)
    if aktif.exists():
        raise ValidationError(f"Masih ada {aktif.count()} sub-unit aktif. Pindahkan atau nonaktifkan sub-unit dahulu.")
    unit.is_active = False
    unit.save(update_fields=["is_active"])
    audit.log(user, "org.deactivate", unit, reason=reason, members=unit.members.count())
    return unit


@transaction.atomic
def activate(unit, user):
    if not can_manage(user):
        raise PermissionDenied
    if unit.parent and not unit.parent.is_active:
        raise ValidationError("Induk unit ini nonaktif. Aktifkan induknya dahulu.")
    unit.is_active = True
    unit.save(update_fields=["is_active"])
    audit.log(user, "org.activate", unit)
    return unit


@transaction.atomic
def add_relation(user, unit, target, kind, note=""):
    if not can_manage(user):
        raise PermissionDenied
    if unit.pk == target.pk:
        raise ValidationError("Unit tidak dapat berhubungan dengan dirinya sendiri.")
    rel, baru = OrganizationRelation.objects.get_or_create(unit=unit, target=target, kind=kind,
                                                          defaults={"note": note})
    if baru:
        audit.log(user, "org.relation.add", unit, target=target, kind=kind)
    return rel


@transaction.atomic
def remove_relation(user, rel):
    if not can_manage(user):
        raise PermissionDenied
    audit.log(user, "org.relation.remove", rel.unit, target=rel.target, kind=rel.kind)
    rel.delete()


# ------------------------------------------------------------------ data awal RSI Yatofa
K = OrganizationUnit.Kind
# (kode, nama, jenis, kode induk struktural). Urutan = urutan bagan. Puncak = Direktur RSI Yatofa (sesuai arahan:
# master dipakai sampai tingkat Direktur; Komisaris & Direktur PT YSW tidak dimasukkan).
RSIY = [
    ("RSIY-DIR", "Direktur RSI Yatofa", K.DIREKSI, None),
    # B. Pengawasan & komite: TANPA induk struktural (lihat RSIY_RELASI)
    ("RSIY-SPI", "Satuan Pengawas Internal (SPI)", K.PENGAWAS, None),
    ("RSIY-KMEDIK", "Komite Medik", K.KOMITE, None),
    ("RSIY-KKEP", "Komite Keperawatan", K.KOMITE, None),
    ("RSIY-KPPI", "Komite PPI", K.KOMITE, None),
    ("RSIY-KKESLAIN", "Komite Kesehatan Lainnya", K.KOMITE, None),
    ("RSIY-K3RS", "Komite K3RS", K.KOMITE, None),
    ("RSIY-KMKP", "Komite KMKP", K.KOMITE, None),
    ("RSIY-KFT", "Komite Farmasi & Terapi", K.KOMITE, None),
    ("RSIY-KETIK", "Komite Etik RS", K.KOMITE, None),
    ("RSIY-KPPRA", "Komite PPRA", K.KOMITE, None),
    ("RSIY-CASEMIX", "Casemix & Asuransi Lainnya", K.UNIT, None),
    # C. Bidang Pelayanan
    ("RSIY-BYAN", "Kepala Bidang Pelayanan", K.BIDANG, "RSIY-DIR"),
    ("RSIY-MGRPP", "Manager Pelayanan Pasien", K.MANAJER, "RSIY-BYAN"),
    ("RSIY-SMEDIK", "Kepala Seksi Pelayanan Medik", K.SEKSI, "RSIY-MGRPP"),
    ("RSIY-IRNA", "Instalasi Rawat Inap", K.INSTALASI, "RSIY-SMEDIK"),
    ("RSIY-IRJA", "Instalasi Rawat Jalan", K.INSTALASI, "RSIY-SMEDIK"),
    ("RSIY-IBS", "Instalasi Bedah Sentral", K.INSTALASI, "RSIY-SMEDIK"),
    ("RSIY-IGD", "Instalasi Gawat Darurat", K.INSTALASI, "RSIY-SMEDIK"),
    ("RSIY-SPENUNJANG", "Kepala Seksi Pelayanan Penunjang", K.SEKSI, "RSIY-MGRPP"),
    ("RSIY-GIZI", "Instalasi Gizi", K.INSTALASI, "RSIY-SPENUNJANG"),
    ("RSIY-FARMASI", "Instalasi Farmasi", K.INSTALASI, "RSIY-SPENUNJANG"),
    ("RSIY-LAB", "Instalasi Laboratorium", K.INSTALASI, "RSIY-SPENUNJANG"),
    ("RSIY-RAD", "Instalasi Radiologi", K.INSTALASI, "RSIY-SPENUNJANG"),
    ("RSIY-CSSD", "Instalasi Pusat Sterilisasi", K.INSTALASI, "RSIY-SPENUNJANG"),
    ("RSIY-RMSIM", "Instalasi Rekam Medis & SIM RS", K.INSTALASI, "RSIY-SPENUNJANG"),
    ("RSIY-KESLING", "Instalasi Kesehatan Lingkungan", K.INSTALASI, "RSIY-SPENUNJANG"),
    ("RSIY-SKEP", "Kepala Seksi Keperawatan", K.SEKSI, "RSIY-MGRPP"),
    ("RSIY-ASKEP", "Asuhan Keperawatan", K.SUBUNIT, "RSIY-SKEP"),
    ("RSIY-ETIKMUTU", "Etik dan Mutu", K.SUBUNIT, "RSIY-SKEP"),
    # D. Bidang Keuangan
    ("RSIY-BKEU", "Kepala Bidang Keuangan", K.BIDANG, "RSIY-DIR"),
    ("RSIY-ANGGARAN", "Perencanaan Anggaran", K.SUBUNIT, "RSIY-BKEU"),
    ("RSIY-AKUNTANSI", "Akuntansi & Pelaporan", K.SUBUNIT, "RSIY-BKEU"),
    ("RSIY-BENDAHARA", "Bendahara", K.SUBUNIT, "RSIY-BKEU"),
    ("RSIY-KASIR", "Kasir", K.SUBUNIT, "RSIY-BKEU"),
    # E. Bidang Umum & Kepegawaian
    ("RSIY-BUMUM", "Kepala Bidang Umum & Kepegawaian", K.BIDANG, "RSIY-DIR"),
    ("RSIY-SHUMAS", "Kepala Seksi Humas & PKRS", K.SEKSI, "RSIY-BUMUM"),
    ("RSIY-HUMAS", "Humas & Pemasaran", K.SUBUNIT, "RSIY-SHUMAS"),
    ("RSIY-PKRS", "Promosi Kesehatan RS", K.SUBUNIT, "RSIY-SHUMAS"),
    ("RSIY-SADM", "Kepala Seksi Administrasi dan Rumah Tangga", K.SEKSI, "RSIY-BUMUM"),
    ("RSIY-TU", "Tata Usaha", K.SUBUNIT, "RSIY-SADM"),
    ("RSIY-PELAPORAN", "Pelaporan", K.SUBUNIT, "RSIY-SADM"),
    ("RSIY-RT", "Rumah Tangga", K.SUBUNIT, "RSIY-SADM"),
    ("RSIY-INVENTORI", "Inventori", K.SUBUNIT, "RSIY-SADM"),
    ("RSIY-IPSRS", "IPSRS", K.SUBUNIT, "RSIY-SADM"),
    ("RSIY-SHRD", "Kepala Seksi HRD", K.SEKSI, "RSIY-BUMUM"),
    ("RSIY-PERSONALIA", "Personalia", K.SUBUNIT, "RSIY-SHRD"),
    ("RSIY-DIKLAT", "Diklat", K.SUBUNIT, "RSIY-SHRD"),
    ("RSIY-SKEAMANAN", "Kepala Seksi Keamanan", K.SEKSI, "RSIY-BUMUM"),
    ("RSIY-ANGGOTA", "Anggota", K.SUBUNIT, "RSIY-SKEAMANAN"),
]
_R = OrganizationRelation.Kind
RSIY_RELASI = [("RSIY-SPI", "RSIY-DIR", _R.PENGAWASAN)] + [
    (kode, "RSIY-DIR", _R.KOORDINASI) for kode, _, jenis, _ in RSIY if jenis in (K.KOMITE,) or kode == "RSIY-CASEMIX"
]


@transaction.atomic
def seed_rsiy(paksa=False):
    """Isi bagan RSI Yatofa. Idempotent: unit dicari berdasarkan kode; unit yang sudah ada TIDAK diubah kecuali
    `paksa=True` (mengembalikan nama/jenis/induk/urutan ke bagan). Tidak menghapus apa pun.
    -> (dibuat, diperbarui, relasi_baru)"""
    dibuat = diperbarui = 0
    peta = {}
    for urutan, (kode, nama, jenis, induk) in enumerate(RSIY, start=1):
        data = {"name": nama, "kind": jenis, "order": urutan, "parent": peta.get(induk) if induk else None}
        unit = OrganizationUnit.objects.filter(code=kode).first()
        if unit is None:
            unit = OrganizationUnit.objects.create(code=kode, **data)
            dibuat += 1
        elif paksa and any(getattr(unit, k) != v for k, v in data.items()):
            if data["parent"] and would_cycle(unit, data["parent"]):
                raise ValidationError(f"{kode}: pengembalian induk akan membuat hubungan melingkar.")
            for k, v in data.items():
                setattr(unit, k, v)
            unit.save()
            diperbarui += 1
        peta[kode] = unit
    relasi = 0
    for asal, tujuan, jenis in RSIY_RELASI:
        _, baru = OrganizationRelation.objects.get_or_create(unit=peta[asal], target=peta[tujuan], kind=jenis)
        relasi += baru
    return dibuat, diperbarui, relasi
