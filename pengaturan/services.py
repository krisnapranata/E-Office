"""Mode aplikasi: DEMO (data contoh dimuat) dan PRODUKSI (data contoh direset, tidak dimuat ulang otomatis).

Data demo = akun berawalan `demo_` (accounts/demo_rsiy.py) + akun demo lama `seed_demo` yang berada di unit demo
lama (DIR/YANMED/IGD/FARM/UMUM), beserta semua data operasional yang mereka buat/terima. Master Organisasi RSI
Yatofa adalah data asli dan TIDAK ikut direset. Yang dihapus hanya data yang DIBUAT akun demo (atau berasal dari
sumber demo); data asli yang merujuk akun demo (mis. tugas asli dengan PIC akun demo) tidak pernah dihapus diam-diam:
reset berjalan dalam satu transaksi dan dibatalkan seluruhnya bila ada rujukan seperti itu.
"""
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import ProtectedError, Q
from django.utils import timezone

from accounts import demo_rsiy
from accounts.management.commands.seed_demo import UNITS as UNIT_DEMO_LAMA, USERS as AKUN_DEMO_LAMA
from accounts.models import OrganizationUnit, User
from accounts.organisasi import can_manage, seed_rsiy
from audit import services as audit

from .models import PengaturanAplikasi

FRASA_RESET = "RESET DATA DEMO"


def akun_demo():
    lama = Q(username__in=[u[0] for u in AKUN_DEMO_LAMA], unit__code__in=[u[0] for u in UNIT_DEMO_LAMA])
    return User.objects.filter(Q(username__startswith=demo_rsiy.AWALAN) | lama)


def is_akun_demo(user):
    return akun_demo().filter(pk=user.pk).exists()


def _cakupan(D):
    """Queryset semua data operasional milik/terkait akun demo `D` (queryset pk)."""
    from agenda.models import AgendaEvent, AgendaMaterial
    from arsip.models import ArchiveDocument, ArchiveVersion
    from instructions.models import Instruction, InstructionTarget
    from letters.models import Disposition, IncomingLetter, OutgoingLetter
    from notulen.models import DecisionAssignee, MeetingDecision, MeetingMinutes
    from workflow.models import Task, TaskEvidence, TaskUpdate, TaskVerification

    surat_masuk = IncomingLetter.objects.filter(created_by__in=D)
    surat_keluar = OutgoingLetter.objects.filter(created_by__in=D)
    disposisi = Disposition.objects.filter(Q(letter__in=surat_masuk) | Q(from_user__in=D))
    instruksi = Instruction.objects.filter(created_by__in=D)
    agenda = AgendaEvent.objects.filter(created_by__in=D)
    notulen = MeetingMinutes.objects.filter(Q(event__in=agenda) | Q(created_by__in=D))
    keputusan = MeetingDecision.objects.filter(minutes__in=notulen)
    tugas_ids = set(Task.objects.filter(
        Q(created_by__in=D) | Q(disposition__in=disposisi)
        | Q(instruction__in=instruksi) | Q(decision__in=keputusan)).values_list("pk", flat=True))
    while True:                                                    # sub-tugas dari tugas yang dihapus
        anak = set(Task.objects.filter(parent_id__in=tugas_ids).exclude(pk__in=tugas_ids).values_list("pk", flat=True))
        if not anak:
            break
        tugas_ids |= anak
    tugas = Task.objects.filter(pk__in=tugas_ids)

    sumber = Q(owner__in=D)
    for qs in (surat_masuk, surat_keluar, instruksi, notulen, tugas):
        ct = ContentType.objects.get_for_model(qs.model)
        sumber |= Q(source_type=ct, source_id__in=list(qs.values_list("pk", flat=True)))
    for model, qs in ((TaskEvidence, TaskEvidence.objects.filter(task__in=tugas)),
                      (AgendaMaterial, AgendaMaterial.objects.filter(event__in=agenda))):
        sumber |= Q(source_type=ContentType.objects.get_for_model(model),
                    source_id__in=list(qs.values_list("pk", flat=True)))
    arsip = ArchiveDocument.objects.filter(sumber)

    return {
        "versi arsip": ArchiveVersion.objects.filter(document__in=arsip),
        "arsip": arsip,
        "verifikasi": TaskVerification.objects.filter(task__in=tugas),
        "bukti": TaskEvidence.objects.filter(task__in=tugas),
        "riwayat progres": TaskUpdate.objects.filter(task__in=tugas),
        "tugas": tugas,
        "penerima keputusan": DecisionAssignee.objects.filter(decision__in=keputusan),
        "notulen": notulen,
        "bahan rapat": AgendaMaterial.objects.filter(event__in=agenda),
        "agenda": agenda,
        "penerima instruksi": InstructionTarget.objects.filter(instruction__in=instruksi),
        "instruksi": instruksi,
        "disposisi": disposisi,
        "surat masuk": surat_masuk,
        "surat keluar": surat_keluar,
    }


def ringkasan():
    """Jumlah data demo yang ada sekarang (untuk halaman Pengaturan)."""
    D = akun_demo().values("pk")
    c = _cakupan(D)
    return {"akun demo": akun_demo().count(), **{k: c[k].count() for k in
            ("surat masuk", "disposisi", "instruksi", "tugas", "agenda", "notulen", "arsip")}}


def _berkas(c):
    """Nama berkas di penyimpanan yang dipakai data demo (dihapus setelah transaksi berhasil)."""
    nama = set()
    for key, field in (("versi arsip", "file"), ("bukti", "file"), ("bahan rapat", "file"), ("notulen", "attachment"),
                       ("instruksi", "attachment"), ("surat masuk", "attachment"), ("surat keluar", "attachment")):
        nama |= {n for n in c[key].values_list(field, flat=True) if n}
    return nama


def _hapus_berlapis(qs):
    """Model dengan `parent` PROTECT ke dirinya sendiri (tugas, disposisi): hapus dari daun ke akar, karena Django
    menolak PROTECT walaupun induknya ikut dihapus dalam batch yang sama."""
    model, ids = qs.model, set(qs.values_list("pk", flat=True))
    while ids:
        punya_anak = set(model.objects.filter(parent_id__in=ids).values_list("parent_id", flat=True))
        daun = ids - punya_anak
        if not daun:                                               # anak di luar cakupan -> biarkan ProtectedError
            model.objects.filter(pk__in=ids).delete()
            return
        model.objects.filter(pk__in=daun).delete()
        ids -= daun


def _cek_admin(user):
    if not can_manage(user):
        raise PermissionDenied


@transaction.atomic
def muat_demo(user=None, password=None):
    """Aktifkan Mode Demo dan muat data contoh (idempotent). `user` None = otomatis saat container start."""
    if user is not None:
        _cek_admin(user)
    password = password or settings.EOFFICE_DEMO_PASSWORD
    if not password:
        raise ValidationError("Isi kata sandi akun demo, atau set EOFFICE_DEMO_PASSWORD di .env server.")
    p = PengaturanAplikasi.objects.select_for_update().get(pk=PengaturanAplikasi.ambil().pk)
    seed_rsiy()
    dibuat, _ = demo_rsiy.buat_pegawai(password)
    alur = demo_rsiy.isi_alur()
    p.mode = PengaturanAplikasi.Mode.DEMO
    p.save()
    audit.log(user, "app.demo.load", p, akun_baru=dibuat, alur=alur or "sudah ada")
    return dibuat, alur


@transaction.atomic
def reset_demo(user, frasa):
    """Hapus seluruh data demo, aktifkan Mode Produksi. Pembangunan ulang tidak memuat data demo lagi."""
    _cek_admin(user)
    if frasa.strip().upper() != FRASA_RESET:
        raise ValidationError(f"Ketik \"{FRASA_RESET}\" untuk konfirmasi.")
    if is_akun_demo(user):
        raise ValidationError("Reset harus dilakukan dengan akun administrator asli (bukan akun demo), karena semua "
                              "akun demo ikut dihapus. Buat akun dengan: manage.py createsuperuser.")
    from notifications.models import Notification

    p = PengaturanAplikasi.objects.select_for_update().get(pk=PengaturanAplikasi.ambil().pk)
    akun = list(akun_demo().values_list("pk", flat=True))
    c = _cakupan(akun)
    berkas = _berkas(c)
    jumlah = {}
    try:
        for key, qs in c.items():                                  # urutan = dari yang merujuk ke yang dirujuk
            jumlah[key] = qs.count()
            _hapus_berlapis(qs) if key in ("tugas", "disposisi") else qs.delete()
        from audit.models import AuditLog

        AuditLog.objects.filter(user_id__in=akun).delete()         # jejak aktivitas akun demo (bukan data asli)
        Notification.objects.filter(recipient_id__in=akun).delete()
        OrganizationUnit.objects.filter(head_id__in=akun).update(head=None)
        jumlah["akun demo"] = User.objects.filter(pk__in=akun).delete()[1].get("accounts.User", 0)
    except ProtectedError as e:
        contoh = ", ".join(str(o) for o in list(e.protected_objects)[:3])
        raise ValidationError(f"Reset dibatalkan, tidak ada data yang dihapus: masih ada data asli yang merujuk data "
                              f"demo ({contoh}). Pindahkan/ubah data tersebut lalu ulangi.")
    unit_lama = 0
    for kode, _, _ in reversed(UNIT_DEMO_LAMA):                     # unit demo lama: hapus bila sudah tidak dipakai
        u = OrganizationUnit.objects.filter(code=kode).first()
        if not u:
            continue
        try:
            with transaction.atomic():
                u.delete()
                unit_lama += 1
        except ProtectedError:
            OrganizationUnit.objects.filter(pk=u.pk).update(is_active=False)
    jumlah["unit demo lama"] = unit_lama
    p.mode = PengaturanAplikasi.Mode.PRODUKSI
    p.direset_pada = timezone.now()
    p.direset_oleh = user
    p.save()
    audit.log(user, "app.demo.reset", p, **jumlah)

    def hapus_berkas():
        from django.core.files.storage import default_storage
        for n in berkas:
            try:
                default_storage.delete(n)
            except OSError:
                pass
    transaction.on_commit(hapus_berkas)
    return jumlah


def muat_otomatis():
    """Dipanggil saat container start: muat demo HANYA bila mode DEMO dan data demo belum ada.
    -> pesan untuk log."""
    seed_rsiy()                                                     # struktur organisasi asli selalu tersedia
    p = PengaturanAplikasi.ambil()
    if not p.is_demo:
        return "Mode produksi: data demo tidak dimuat."
    if demo_rsiy.sudah_ada_alur():
        return "Mode demo: data demo sudah ada, dilewati."
    if not settings.EOFFICE_DEMO_PASSWORD:
        return "Mode demo: EOFFICE_DEMO_PASSWORD belum diisi di .env, data demo TIDAK dimuat."
    dibuat, alur = muat_demo()
    return f"Mode demo: {dibuat} akun demo dibuat; isian alur: {alur}."
