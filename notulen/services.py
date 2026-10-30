"""E-Notulen & Keputusan. Alur: notulis menulis draf + butir keputusan → diajukan → pimpinan rapat (penyelenggara
agenda) menyetujui atau mengembalikan. Saat disetujui, setiap penerima keputusan yang memerlukan tindakan menjadi
SATU tugas `KEPUTUSAN_RAPAT` (tanpa duplikasi) — itulah tindak lanjut (E-Follow Up)."""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Max
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role
from agenda.models import AgendaEvent
from agenda.services import can_view_event, visible_events
from audit import services as audit
from notifications import services as notify
from workflow import services as workflow
from workflow.models import Task, TaskSource

from .models import DecisionAssignee, MeetingDecision, MeetingMinutes


def can_write_minutes(user, event):
    """Notulis: pembuat/penyelenggara agenda, sekretariat, atau peserta berperan pejabat."""
    if user.role == Role.AUDITOR or not can_view_event(user, event):
        return False
    if user.role in (Role.DIREKTUR, Role.SEKRETARIS) or user.pk in (event.created_by_id, event.organizer_id):
        return True
    return user.role in (Role.WADIR, Role.KEPALA_UNIT) and event.participants.filter(pk=user.pk).exists()


def can_edit(user, minutes):
    return minutes.editable and can_write_minutes(user, minutes.event) and (
        user.pk in (minutes.created_by_id, minutes.event.organizer_id) or user.role == Role.DIREKTUR)


def can_approve(user, minutes):
    return user.pk == minutes.event.organizer_id


def visible_minutes(user):
    return MeetingMinutes.objects.filter(event__in=visible_events(user))


def _url(minutes):
    return reverse("notulen:detail", args=[minutes.pk])


@transaction.atomic
def create_minutes(user, event, attendees=(), **fields):
    if not event.is_meeting:
        raise ValidationError("Notulen hanya untuk agenda berjenis Rapat.")
    if event.status == AgendaEvent.Status.DIBATALKAN:
        raise ValidationError("Rapat dibatalkan.")
    if not can_write_minutes(user, event):
        raise PermissionDenied
    if MeetingMinutes.objects.filter(event=event).exists():
        raise ValidationError("Rapat ini sudah memiliki notulen.")
    m = MeetingMinutes(event=event, created_by=user, **fields)
    m.save()
    m.attendees.set(attendees)
    audit.log(user, "minutes.create", m)
    return m


@transaction.atomic
def update_minutes(minutes, user, attendees=None, **fields):
    if not can_edit(user, minutes):
        raise PermissionDenied
    for k, v in fields.items():
        if k == "attachment" and not v:
            continue
        setattr(minutes, k, v)
    minutes.save()
    if attendees is not None:
        minutes.attendees.set(attendees)
    audit.log(user, "minutes.edit", minutes)
    return minutes


@transaction.atomic
def add_decision(minutes, user, **fields):
    if not can_edit(user, minutes):
        raise PermissionDenied
    if fields.get("requires_action") and not fields.get("due_date"):
        raise ValidationError({"due_date": "Keputusan yang memerlukan tindakan wajib memiliki tenggat."})
    nomor = (minutes.decisions.aggregate(n=Max("number"))["n"] or 0) + 1
    d = MeetingDecision.objects.create(minutes=minutes, number=nomor, **fields)
    audit.log(user, "minutes.decision.add", minutes, number=nomor, requires_action=d.requires_action)
    return d


@transaction.atomic
def remove_decision(decision, user):
    if not can_edit(user, decision.minutes):
        raise PermissionDenied
    audit.log(user, "minutes.decision.remove", decision.minutes, number=decision.number)
    decision.delete()


@transaction.atomic
def add_assignee(decision, user, unit, pic):
    if not can_edit(user, decision.minutes):
        raise PermissionDenied
    if not decision.requires_action:
        raise ValidationError("Keputusan ini tidak memerlukan tindakan.")
    a, _ = DecisionAssignee.objects.get_or_create(decision=decision, unit=unit, pic=pic)
    return a


@transaction.atomic
def remove_assignee(assignee, user):
    if not can_edit(user, assignee.decision.minutes):
        raise PermissionDenied
    assignee.delete()


def _validate_for_submit(minutes):
    errors = []
    if not minutes.discussion.strip():
        errors.append("Pokok pembahasan wajib diisi.")
    for d in minutes.decisions.all():
        if d.requires_action and not d.assignees.exists():
            errors.append(f"Keputusan {d.number} memerlukan tindakan tetapi belum memiliki PIC/unit.")
    if errors:
        raise ValidationError(errors)


@transaction.atomic
def submit(minutes, user):
    if not can_edit(user, minutes):
        raise PermissionDenied
    _validate_for_submit(minutes)
    minutes.status = MeetingMinutes.Status.DIAJUKAN
    minutes.revision += 1
    minutes.return_note = ""
    minutes.save()
    audit.log(user, "minutes.submit", minutes, revision=minutes.revision)
    if minutes.event.organizer_id != user.pk:
        notify.send(minutes.event.organizer, "minutes.approval", f"Notulen menunggu persetujuan: {minutes.event.title}",
                    "", _url(minutes))
    return minutes


@transaction.atomic
def return_minutes(minutes, user, note):
    if not can_approve(user, minutes) or minutes.status != MeetingMinutes.Status.DIAJUKAN:
        raise PermissionDenied
    if not note.strip():
        raise ValidationError({"note": "Catatan pengembalian wajib diisi."})
    minutes.status = MeetingMinutes.Status.DRAF
    minutes.return_note = note
    minutes.save()
    audit.log(user, "minutes.return", minutes, note=note)
    notify.send(minutes.created_by, "minutes.returned", f"Notulen dikembalikan: {minutes.event.title}", note,
                _url(minutes))
    return minutes


@transaction.atomic
def approve(minutes, user):
    """Setujui notulen: kunci isi, tandai rapat selesai, buat tugas tindak lanjut untuk setiap penerima."""
    minutes = MeetingMinutes.objects.select_for_update().get(pk=minutes.pk)
    if not can_approve(user, minutes) or minutes.status != MeetingMinutes.Status.DIAJUKAN:
        raise PermissionDenied
    _validate_for_submit(minutes)
    minutes.status = MeetingMinutes.Status.DISETUJUI
    minutes.approved_by = user
    minutes.approved_at = timezone.now()
    minutes.save()
    event = minutes.event
    if event.status == AgendaEvent.Status.TERJADWAL:
        event.status = AgendaEvent.Status.SELESAI
        event.save(update_fields=["status", "updated_at"])
    dibuat = 0
    for d in minutes.decisions.filter(requires_action=True).prefetch_related("assignees__unit", "assignees__pic"):
        for a in d.assignees.all():
            if Task.objects.filter(decision=d, unit=a.unit, pic=a.pic).exists():
                continue
            workflow.create_task(
                created_by=user,
                title=f"Tindak lanjut rapat: {d.text}"[:255],
                description=f"Rapat {event.title} ({timezone.localtime(event.start):%d-%m-%Y}), keputusan {d.number}:\n{d.text}",
                source_type=TaskSource.KEPUTUSAN_RAPAT, decision=d, unit=a.unit, pic=a.pic,
                priority=d.priority, classification=event.classification,
                start_date=timezone.localdate(), due_date=d.due_date,
                completion_criteria=d.completion_criteria, verifier=event.organizer,
            )
            dibuat += 1
    audit.log(user, "minutes.approve", minutes, revision=minutes.revision, follow_ups=dibuat)
    if minutes.created_by_id != user.pk:
        notify.send(minutes.created_by, "minutes.approved", f"Notulen disetujui: {event.title}", "", _url(minutes))
    from arsip.services import arsipkan_notulen

    arsipkan_notulen(minutes)
    return minutes
