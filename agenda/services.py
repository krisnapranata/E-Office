"""E-Agenda: jadwal Direktur, rapat, kegiatan. Undangan, perubahan, pembatalan, dan pengingat lewat notifikasi."""
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role
from accounts.permissions import Classification
from audit import services as audit
from notifications import services as notify

from .models import AgendaEvent, AgendaMaterial, AgendaReminderLog

ORGANIZER_ROLES = {Role.DIREKTUR, Role.WADIR, Role.KEPALA_UNIT, Role.SEKRETARIS}


def can_create_event(user):
    return user.is_authenticated and user.role in ORGANIZER_ROLES


def visible_events(user, qs=None):
    qs = AgendaEvent.objects.all() if qs is None else qs
    if user.role == Role.DIREKTUR:
        return qs
    cond = Q(created_by=user) | Q(organizer=user) | Q(participants=user)
    if user.role in (Role.SEKRETARIS, Role.AUDITOR):
        cond |= ~Q(classification=Classification.RAHASIA)
    return qs.filter(cond).distinct()


def can_view_event(user, event):
    return visible_events(user, AgendaEvent.objects.filter(pk=event.pk)).exists()


def can_manage_event(user, event):
    return user.role != Role.AUDITOR and (
        user.role == Role.DIREKTUR or user.pk in (event.created_by_id, event.organizer_id))


def _label(event):
    return "(rahasia)" if event.classification == Classification.RAHASIA else event.title


def _url(event):
    return reverse("agenda:detail", args=[event.pk])


def _waktu(event):
    return f"{timezone.localtime(event.start):%d-%m-%Y %H:%M}"


def _invite(event, users, kind, title, message=""):
    for u in users:
        notify.send(u, kind, title, message, _url(event))


def _validate(event):
    if event.end and event.end <= event.start:
        raise ValidationError({"end": "Waktu selesai harus setelah waktu mulai."})


@transaction.atomic
def create_event(user, participants=(), **fields):
    if not can_create_event(user):
        raise PermissionDenied
    fields.setdefault("organizer", user)
    event = AgendaEvent(created_by=user, **fields)
    _validate(event)
    event.save()
    event.participants.set(participants)
    audit.log(user, "agenda.create", event, start=event.start, organizer=event.organizer)
    penerima = {*participants, event.organizer} - {user}
    _invite(event, penerima, "agenda.invite", f"Undangan {event.get_kind_display().lower()}: {_label(event)}",
            f"{_waktu(event)} · {event.location or event.link or 'lokasi menyusul'}")
    return event


@transaction.atomic
def update_event(event, user, participants=None, **fields):
    if not can_manage_event(user, event):
        raise PermissionDenied
    if event.status != AgendaEvent.Status.TERJADWAL:
        raise ValidationError("Agenda yang sudah selesai/dibatalkan tidak dapat diubah.")
    lama = (event.start, event.end, event.location, event.link)
    sebelum = set(event.participants.all())
    for k, v in fields.items():
        setattr(event, k, v)
    _validate(event)
    event.save()
    if participants is not None:
        event.participants.set(participants)
    sesudah = set(event.participants.all())
    berubah = lama != (event.start, event.end, event.location, event.link)
    audit.log(user, "agenda.update", event, jadwal_berubah=berubah, start=event.start)
    if berubah:
        _invite(event, ((sebelum & sesudah) | {event.organizer}) - {user}, "agenda.reschedule",
                f"Perubahan jadwal: {_label(event)}", f"Menjadi {_waktu(event)} · {event.location or event.link}")
    _invite(event, sesudah - sebelum - {user}, "agenda.invite", f"Undangan: {_label(event)}", _waktu(event))
    return event


@transaction.atomic
def cancel_event(event, user, reason):
    if not can_manage_event(user, event):
        raise PermissionDenied
    if not reason.strip():
        raise ValidationError({"reason": "Alasan pembatalan wajib diisi."})
    if event.status != AgendaEvent.Status.TERJADWAL:
        raise ValidationError("Agenda tidak dalam status terjadwal.")
    event.status = AgendaEvent.Status.DIBATALKAN
    event.cancelled_reason = reason
    event.save()
    audit.log(user, "agenda.cancel", event, reason=reason)
    _invite(event, (set(event.participants.all()) | {event.organizer}) - {user}, "agenda.cancel",
            f"Dibatalkan: {_label(event)}", reason if event.classification != Classification.RAHASIA else "")
    return event


@transaction.atomic
def complete_event(event, user):
    if not can_manage_event(user, event):
        raise PermissionDenied
    if event.status == AgendaEvent.Status.TERJADWAL:
        event.status = AgendaEvent.Status.SELESAI
        event.save(update_fields=["status", "updated_at"])
        audit.log(user, "agenda.complete", event)
    return event


@transaction.atomic
def add_material(event, user, uploaded_file, description=""):
    if not (can_manage_event(user, event) or event.participants.filter(pk=user.pk).exists()):
        raise PermissionDenied
    m = AgendaMaterial(event=event, file=uploaded_file, original_name=uploaded_file.name[:255],
                       description=description, uploaded_by=user)
    m.full_clean()
    m.save()
    audit.log(user, "agenda.material", event, file=m.original_name)
    from arsip.services import arsipkan_bahan

    arsipkan_bahan(m)
    return m


def run_agenda_reminders(today=None):
    """Pengingat H-n sebelum kegiatan (default H-1 dan hari-H). Idempotent lewat AgendaReminderLog."""
    today = today or timezone.localdate()
    sent = 0
    for days in settings.EOFFICE.get("AGENDA_REMINDER_DAYS", [1, 0]):
        tanggal = today + timedelta(days=days)
        acara = AgendaEvent.objects.filter(status=AgendaEvent.Status.TERJADWAL, start__date=tanggal)
        for event in acara.select_related("organizer").prefetch_related("participants"):
            for u in {event.organizer, *event.participants.all()}:
                try:
                    with transaction.atomic():
                        AgendaReminderLog.objects.create(event=event, recipient=u, days_offset=days,
                                                         start_date=tanggal)
                except IntegrityError:
                    continue
                kapan = "hari ini" if days == 0 else ("besok" if days == 1 else f"{days} hari lagi")
                notify.send(u, "agenda.reminder", f"Pengingat agenda {kapan}: {_label(event)}",
                            f"{_waktu(event)} · {event.location or event.link}", _url(event))
                sent += 1
    return sent
