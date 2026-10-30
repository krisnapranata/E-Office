"""E-Arsip: katalog dokumen bermetadata, versi, hak akses, retensi & pemusnahan.

- Dokumen modul lain diarsipkan OTOMATIS lewat `arsipkan()` dan MERUJUK objek asalnya (tidak menyalin berkas;
  versi menunjuk berkas yang sama). Hak lihat dokumen bersumber = hak lihat objek asalnya.
- Retensi: tanggal dokumen + `EOFFICE["RETENTION_YEARS"]` (per jenis, default 5 tahun) — nilai menunggu kebijakan RS.
- Pemusnahan dua langkah: petugas arsip MENGUSULKAN (hanya setelah masa retensi), Direktur MENYETUJUI. Metadata
  dan berita acara tetap disimpan; unduhan berkas ditutup. Tidak ada penghapusan dokumen dari aplikasi.
"""
from datetime import date

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import Role
from accounts.permissions import Classification, managed_unit_ids
from audit import services as audit

from .models import ArchiveDocument, ArchiveVersion

T = ArchiveDocument.DocType
ARCHIVIST_ROLES = {Role.ARSIP, Role.SEKRETARIS}
READ_ALL_ROLES = {Role.ARSIP, Role.SEKRETARIS, Role.AUDITOR}


def retention_years(doc_type):
    cfg = settings.EOFFICE.get("RETENTION_YEARS", {})
    return int(cfg.get(doc_type, cfg.get("DEFAULT", 5)))


def retention_date(doc_type, doc_date):
    try:
        return doc_date.replace(year=doc_date.year + retention_years(doc_type))
    except ValueError:      # 29 Feb
        return doc_date.replace(year=doc_date.year + retention_years(doc_type), day=28)


# ------------------------------------------------------------------ hak akses
def visible_archives(user, qs=None):
    qs = ArchiveDocument.objects.all() if qs is None else qs
    if user.role == Role.DIREKTUR:
        return qs
    rahasia = Q(classification=Classification.RAHASIA)
    cond = Q(owner=user)
    if user.role in READ_ALL_ROLES:
        cond |= ~rahasia
    units = managed_unit_ids(user)
    if units:
        cond |= Q(unit_id__in=units) & ~rahasia
    return qs.filter(cond)


def _source_visible(user, doc):
    src = doc.source
    if src is None:
        return False
    nama = src._meta.label
    if nama == "letters.IncomingLetter":
        from letters.services import can_view_letter
        return can_view_letter(user, src)
    if nama == "letters.OutgoingLetter":
        from letters.services import visible_outgoing
        return visible_outgoing(user).filter(pk=src.pk).exists()
    if nama == "instructions.Instruction":
        from instructions.services import can_view_instruction
        return can_view_instruction(user, src)
    if nama == "workflow.TaskEvidence":
        from workflow.access import can_view_task
        return can_view_task(user, src.task)
    if nama in ("agenda.AgendaMaterial", "notulen.MeetingMinutes"):
        from agenda.services import can_view_event
        return can_view_event(user, src.event)
    return False


def can_view_archive(user, doc):
    return visible_archives(user, ArchiveDocument.objects.filter(pk=doc.pk)).exists() or _source_visible(user, doc)


def can_manage_archive(user):
    return user.role in ARCHIVIST_ROLES


# ------------------------------------------------------------------ pengarsipan
@transaction.atomic
def arsipkan(source, berkas, *, doc_type, title, owner, doc_date=None, number="", unit=None,
             classification=Classification.BIASA, keywords="", note=""):
    """Arsipkan berkas milik objek `source` (idempotent). Berkas baru pada objek yang sama = versi baru."""
    if not berkas:
        return None
    ct = ContentType.objects.get_for_model(source)
    doc_date = doc_date or timezone.localdate()
    doc, baru = ArchiveDocument.objects.get_or_create(
        source_type=ct, source_id=source.pk, doc_type=doc_type,
        defaults=dict(title=title[:255], number=number, doc_date=doc_date, owner=owner, unit=unit,
                      classification=classification, keywords=keywords,
                      retention_until=retention_date(doc_type, doc_date)))
    terakhir = doc.latest
    if terakhir and terakhir.file.name == berkas.name:
        return doc
    nama = getattr(berkas, "original_name", None) or berkas.name.rsplit("/", 1)[-1]
    v = ArchiveVersion(document=doc, version=(terakhir.version + 1) if terakhir else 1, original_name=nama[:255],
                       uploaded_by=owner, note=note or ("Diarsipkan otomatis" if baru else "Revisi berkas"))
    v.file.name = berkas.name            # merujuk berkas yang sama, tidak menyalin
    v.save()
    if not baru and doc.classification != classification:
        doc.classification = classification
        doc.save(update_fields=["classification"])
    audit.log(owner, "archive.version" if not baru else "archive.create", doc, version=v.version, auto=True)
    return doc


def arsipkan_surat_masuk(letter):
    return arsipkan(letter, letter.attachment, doc_type=T.SURAT_MASUK, title=letter.subject,
                    number=letter.letter_number, doc_date=letter.letter_date, owner=letter.created_by,
                    unit=letter.created_by.unit, classification=letter.classification,
                    keywords=f"{letter.agenda_number} {letter.sender}")


def arsipkan_surat_keluar(letter):
    return arsipkan(letter, letter.attachment, doc_type=T.SURAT_KELUAR, title=letter.subject,
                    number=letter.letter_number, doc_date=letter.letter_date, owner=letter.created_by,
                    unit=letter.created_by.unit, classification=letter.classification, keywords=letter.recipient)


def arsipkan_instruksi(ins):
    return arsipkan(ins, ins.attachment, doc_type=T.INSTRUKSI, title=ins.title, number=ins.code,
                    doc_date=ins.instruction_date, owner=ins.created_by, unit=ins.created_by.unit,
                    classification=ins.classification)


def arsipkan_bukti(ev):
    t = ev.task
    return arsipkan(ev, ev.file, doc_type=T.BUKTI, title=f"Bukti T-{t.pk} {t.title}", number=f"T-{t.pk}",
                    doc_date=timezone.localtime(ev.uploaded_at).date() if ev.uploaded_at else None,
                    owner=ev.uploaded_by, unit=t.unit, classification=t.classification,
                    keywords=ev.description)


def arsipkan_bahan(m):
    e = m.event
    return arsipkan(m, m.file, doc_type=T.AGENDA, title=f"{m.original_name} — {e.title}",
                    doc_date=timezone.localtime(e.start).date(), owner=m.uploaded_by, unit=m.uploaded_by.unit,
                    classification=e.classification, keywords=m.description)


def arsipkan_notulen(minutes):
    e = minutes.event
    return arsipkan(minutes, minutes.attachment, doc_type=T.NOTULEN, title=f"Notulen {e.title}",
                    doc_date=timezone.localtime(e.start).date(), owner=minutes.created_by,
                    unit=minutes.created_by.unit, classification=e.classification,
                    note=f"Disetujui (revisi {minutes.revision})")


# ------------------------------------------------------------------ arsip manual, versi, pemusnahan
@transaction.atomic
def create_manual(user, berkas, **fields):
    if not can_manage_archive(user):
        raise PermissionDenied
    doc = ArchiveDocument(owner=user, **fields)
    doc.retention_until = retention_date(doc.doc_type, doc.doc_date)
    doc.save()
    v = ArchiveVersion(document=doc, version=1, file=berkas, original_name=berkas.name[:255], uploaded_by=user,
                       note="Unggahan awal")
    v.full_clean()
    v.save()
    audit.log(user, "archive.create", doc, doc_type=doc.doc_type)
    return doc


@transaction.atomic
def add_version(doc, user, berkas, note=""):
    if not (can_manage_archive(user) or doc.owner_id == user.pk) or doc.source_id:
        raise PermissionDenied     # versi dokumen bersumber mengikuti objek asalnya
    if doc.status != ArchiveDocument.Status.AKTIF:
        raise ValidationError("Dokumen tidak aktif.")
    if not note.strip():
        raise ValidationError({"note": "Catatan versi (alasan revisi) wajib diisi."})
    v = ArchiveVersion(document=doc, version=doc.latest.version + 1, file=berkas, original_name=berkas.name[:255],
                       uploaded_by=user, note=note)
    v.full_clean()
    v.save()
    audit.log(user, "archive.version", doc, version=v.version, note=note)
    return v


@transaction.atomic
def update_metadata(doc, user, **fields):
    if not can_manage_archive(user):
        raise PermissionDenied
    lama = {k: getattr(doc, k) for k in fields}
    for k, v in fields.items():
        setattr(doc, k, v)
    if "doc_date" in fields or "doc_type" in fields:
        doc.retention_until = retention_date(doc.doc_type, doc.doc_date)
    doc.save()
    audit.log(user, "archive.metadata", doc, **{k: (lama[k], fields[k]) for k in fields if lama[k] != fields[k]})
    return doc


@transaction.atomic
def propose_disposal(doc, user, note, today=None):
    if user.role != Role.ARSIP:
        raise PermissionDenied
    today = today or timezone.localdate()
    if doc.status != ArchiveDocument.Status.AKTIF:
        raise ValidationError("Dokumen tidak aktif.")
    if doc.retention_until > today:
        raise ValidationError(f"Masa retensi belum berakhir (sampai {doc.retention_until:%d-%m-%Y}).")
    if not note.strip():
        raise ValidationError({"note": "Alasan/usulan pemusnahan wajib diisi."})
    doc.status = ArchiveDocument.Status.DIUSULKAN
    doc.disposal_note = note
    doc.disposal_proposed_by = user
    doc.save()
    audit.log(user, "archive.dispose.propose", doc, note=note)
    from notifications import services as notify
    from django.urls import reverse
    from accounts.models import User

    for d in User.objects.filter(role=Role.DIREKTUR, is_active=True):
        notify.send(d, "archive.disposal", f"Usulan pemusnahan arsip: {doc.number or doc.pk}", note,
                    reverse("arsip:detail", args=[doc.pk]))
    return doc


@transaction.atomic
def decide_disposal(doc, user, *, approved, note=""):
    if user.role != Role.DIREKTUR:
        raise PermissionDenied
    if doc.status != ArchiveDocument.Status.DIUSULKAN:
        raise ValidationError("Tidak ada usulan pemusnahan.")
    if approved:
        if not note.strip():
            raise ValidationError({"note": "Berita acara pemusnahan wajib diisi."})
        doc.status = ArchiveDocument.Status.DIMUSNAHKAN
        doc.disposal_note = f"{doc.disposal_note}\n\nBerita acara: {note}"
        doc.disposal_approved_by = user
        doc.disposed_at = timezone.now()
    else:
        doc.status = ArchiveDocument.Status.AKTIF
        doc.disposal_note = f"{doc.disposal_note}\n\nDitolak: {note}".strip()
    doc.save()
    audit.log(user, "archive.dispose.approve" if approved else "archive.dispose.reject", doc, note=note)
    return doc


def due_for_disposal(today=None):
    return ArchiveDocument.objects.filter(status=ArchiveDocument.Status.AKTIF,
                                          retention_until__lte=today or date.today())
