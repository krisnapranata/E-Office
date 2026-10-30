"""Mesin status tugas bersama. Semua perubahan status melewati modul ini."""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from audit import services as audit
from notifications import services as notify

from .access import can_manage_task, can_report_progress, can_verify
from .models import Task, TaskEvidence, TaskStatus, TaskUpdate, TaskVerification

S = TaskStatus

ALLOWED_TRANSITIONS = {
    S.DRAF: {S.MENUNGGU_PENERIMAAN, S.DIBATALKAN},
    S.MENUNGGU_PENERIMAAN: {S.BELUM_DIMULAI, S.DIBATALKAN},
    S.BELUM_DIMULAI: {S.BERJALAN, S.TERHAMBAT, S.DIBATALKAN},
    S.BERJALAN: {S.TERHAMBAT, S.MENUNGGU_VERIFIKASI, S.SELESAI, S.DIBATALKAN},
    S.TERHAMBAT: {S.BERJALAN, S.DIBATALKAN},
    S.MENUNGGU_VERIFIKASI: {S.SELESAI, S.PERLU_PERBAIKAN, S.DIBATALKAN},
    S.PERLU_PERBAIKAN: {S.BERJALAN, S.TERHAMBAT, S.MENUNGGU_VERIFIKASI, S.DIBATALKAN},
    S.SELESAI: set(),
    S.DIBATALKAN: set(),
}

# Status yang dapat dipilih PIC saat melaporkan progres.
PROGRESS_STATUSES = (S.BERJALAN, S.TERHAMBAT)


class TransitionError(ValidationError):
    pass


def can_transition(task, target):
    return target in ALLOWED_TRANSITIONS[task.status]


def _set_status(task, target, user):
    if task.status == target:
        return
    if not can_transition(task, target):
        raise TransitionError(
            f"Status tidak dapat diubah dari {task.get_status_display()} "
            f"ke {S(target).label}."
        )
    old = task.status
    task.status = target
    if target in (S.SELESAI, S.DIBATALKAN):
        task.closed_at = timezone.now()
    audit.log(user, "task.status", task, status=(old, target))


def validate_task(task):
    """Aturan bisnis Bab 8: judul, sumber/alasan, PIC/unit, tenggat bila diwajibkan."""
    errors = {}
    if not task.title.strip():
        errors["title"] = "Judul wajib diisi."
    if task.source_type == "LANGSUNG" and not task.source_note.strip():
        errors["source_note"] = "Penugasan langsung wajib mencantumkan alasan."
    if task.source_type == "INSTRUKSI" and not task.instruction_id:
        errors["instruction"] = "Tugas dari instruksi wajib tertaut ke instruksi."
    if task.source_type == "KEPUTUSAN_RAPAT" and not task.decision_id:
        errors["decision"] = "Tugas dari keputusan rapat wajib tertaut ke keputusan."
    if task.source_type == "DISPOSISI" and not task.disposition_id:
        errors["disposition"] = "Tugas dari disposisi wajib tertaut ke disposisi."
    if task.due_date and task.start_date and task.due_date < task.start_date:
        errors["due_date"] = "Tenggat tidak boleh sebelum tanggal mulai."
    if errors:
        raise ValidationError(errors)


@transaction.atomic
def create_task(*, created_by, issue=True, collaborators=(), **fields):
    fields.setdefault("verifier", created_by)
    task = Task(created_by=created_by, **fields)
    validate_task(task)
    task.save()
    if collaborators:
        task.collaborators.set(collaborators)
    audit.log(created_by, "task.create", task, source=task.source_type, pic=task.pic,
              due_date=task.due_date)
    if issue:
        issue_task(task, created_by)
    return task


@transaction.atomic
def issue_task(task, user):
    _set_status(task, S.MENUNGGU_PENERIMAAN, user)
    task.save()
    notify.task_assigned(task)
    return task


@transaction.atomic
def accept_task(task, user):
    if user.pk != task.pic_id:
        raise PermissionDenied
    _set_status(task, S.BELUM_DIMULAI, user)
    task.save()
    TaskUpdate.objects.create(task=task, author=user, status_from=S.MENUNGGU_PENERIMAAN,
                              status_to=S.BELUM_DIMULAI, note="Tugas diterima.")
    return task


@transaction.atomic
def report_progress(task, user, *, progress, status, note="", obstacle="", decision_needed=""):
    if not can_report_progress(user, task):
        raise PermissionDenied
    if status not in PROGRESS_STATUSES:
        raise TransitionError("Status progres harus Berjalan atau Terhambat.")
    if not 0 <= progress <= 100:
        raise ValidationError({"progress": "Progres harus 0–100."})
    if status == S.TERHAMBAT and not obstacle.strip():
        raise ValidationError({"obstacle": "Jelaskan hambatan bila status Terhambat."})
    old_status = task.status
    _set_status(task, status, user)
    # Progres 100% tidak otomatis menutup tugas (Bab 8); penutupan lewat submit/verifikasi.
    task.progress = progress
    task.save()
    TaskUpdate.objects.create(
        task=task, author=user, progress=progress, status_from=old_status, status_to=status,
        note=note, obstacle=obstacle, decision_needed=decision_needed,
    )
    return task


@transaction.atomic
def add_evidence(task, user, uploaded_file, description=""):
    if not can_report_progress(user, task):
        raise PermissionDenied
    if task.is_closed:
        raise TransitionError("Tugas sudah ditutup.")
    ev = TaskEvidence(task=task, file=uploaded_file, original_name=uploaded_file.name[:255],
                      description=description, uploaded_by=user)
    ev.full_clean()
    ev.save()
    audit.log(user, "task.evidence", task, file=ev.original_name)
    from arsip.services import arsipkan_bukti

    arsipkan_bukti(ev)
    return ev


@transaction.atomic
def submit_result(task, user, note=""):
    if user.pk != task.pic_id:
        raise PermissionDenied
    if task.requires_evidence and not task.evidences.exists():
        raise ValidationError("Unggah minimal satu bukti sebelum mengirim hasil.")
    old = task.status
    target = S.MENUNGGU_VERIFIKASI if task.requires_verification else S.SELESAI
    _set_status(task, target, user)
    task.progress = 100
    task.submitted_at = timezone.now()
    task.save()
    TaskUpdate.objects.create(task=task, author=user, progress=100, status_from=old,
                              status_to=target, note=note or "Hasil dikirim.")
    if target == S.MENUNGGU_VERIFIKASI:
        notify.verification_requested(task)
    else:
        _on_closed(task)
    return task


@transaction.atomic
def verify(task, user, *, approved, note=""):
    if not can_verify(user, task):
        raise PermissionDenied
    if task.status != S.MENUNGGU_VERIFIKASI:
        raise TransitionError("Tugas tidak sedang menunggu verifikasi.")
    if not approved and not note.strip():
        raise ValidationError({"note": "Alasan perbaikan wajib diisi."})
    decision = (TaskVerification.Decision.DISETUJUI if approved
                else TaskVerification.Decision.PERLU_PERBAIKAN)
    TaskVerification.objects.create(task=task, verifier=user, decision=decision, note=note)
    _set_status(task, S.SELESAI if approved else S.PERLU_PERBAIKAN, user)
    task.save()
    audit.log(user, "task.verify", task, decision=decision, note=note)
    if approved:
        _on_closed(task)
    else:
        notify.revision_requested(task, note)
    return task


@transaction.atomic
def cancel(task, user, reason):
    if not can_manage_task(user, task):
        raise PermissionDenied
    if not reason.strip():
        raise ValidationError({"reason": "Alasan pembatalan wajib diisi."})
    _set_status(task, S.DIBATALKAN, user)
    task.save()
    audit.log(user, "task.cancel", task, reason=reason)
    notify.task_closed(task)
    return task


@transaction.atomic
def reassign(task, user, *, pic=None, due_date=None, reason):
    """Perubahan PIC/tenggat setelah penugasan wajib mencatat alasan (Bab 8)."""
    if not can_manage_task(user, task):
        raise PermissionDenied
    if task.is_closed:
        raise TransitionError("Tugas sudah ditutup.")
    if not reason.strip():
        raise ValidationError({"reason": "Alasan perubahan wajib diisi."})
    changes = {}
    if pic and pic.pk != task.pic_id:
        changes["pic"] = (task.pic, pic)
        task.pic = pic
    if due_date and due_date != task.due_date:
        changes["due_date"] = (task.due_date, due_date)
        task.due_date = due_date
    if not changes:
        return task
    task.save()
    audit.log(user, "task.reassign", task, reason=reason, **changes)
    TaskUpdate.objects.create(task=task, author=user, note=f"Perubahan penugasan: {reason}")
    if "pic" in changes:
        notify.task_assigned(task)
    return task


@transaction.atomic
def give_direction(task, user, note):
    """Pimpinan menjawab hambatan/keputusan yang dibutuhkan PIC (PRD 6.5: hambatan & keputusan yang dibutuhkan).
    Dicatat di riwayat tugas sebagai pembaruan dari pimpinan; PIC dinotifikasi."""
    if not can_manage_task(user, task):
        raise PermissionDenied
    if task.is_closed:
        raise TransitionError("Tugas sudah ditutup.")
    if not note.strip():
        raise ValidationError({"note": "Tuliskan arahan Anda."})
    upd = TaskUpdate.objects.create(task=task, author=user, note=f"Arahan pimpinan: {note.strip()}")
    audit.log(user, "task.direction", task, note=note.strip())
    notify.direction_given(task, user)
    return upd


def menunggu_arahan(task_qs):
    """Tugas terbuka yang PIC-nya meminta keputusan dan belum dijawab pimpinan.
    Jawaban = pembaruan SESUDAHNYA oleh orang yang bukan PIC/kolaborator (lihat give_direction).
    -> [(task, update_permintaan)]"""
    terbuka = task_qs.exclude(status__in=[S.SELESAI, S.DIBATALKAN, S.DRAF])
    minta = (TaskUpdate.objects.filter(task__in=terbuka).exclude(decision_needed="")
             .select_related("task", "task__pic", "task__unit", "author").order_by("task_id", "-created_at", "-id"))
    hasil, dilihat = [], set()
    for u in minta:
        if u.task_id in dilihat:
            continue
        dilihat.add(u.task_id)
        pelaksana = {u.task.pic_id, *u.task.collaborators.values_list("pk", flat=True)}
        dijawab = (TaskUpdate.objects.filter(task_id=u.task_id, created_at__gte=u.created_at).exclude(pk=u.pk)
                   .exclude(author_id__in=pelaksana).exists())
        if not dijawab:
            hasil.append((u.task, u))
    hasil.sort(key=lambda x: x[1].created_at)
    return hasil


def request_update(task, user):
    if not can_manage_task(user, task):
        raise PermissionDenied
    audit.log(user, "task.request_update", task)
    notify.update_requested(task, user)


def _on_closed(task):
    notify.task_closed(task)
    if task.disposition_id:
        from letters.services import sync_disposition_status

        sync_disposition_status(task.disposition)
