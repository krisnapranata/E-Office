from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import Role
from accounts.permissions import Classification, can_dispose, can_register_letter
from audit import services as audit
from config.numbering import next_number
from notifications import services as notify
from workflow import services as workflow
from workflow.models import TaskSource, TaskStatus

from .models import Disposition, IncomingLetter, OutgoingLetter


def visible_letters(user, qs=None):
    qs = IncomingLetter.objects.all() if qs is None else qs
    if user.role == Role.DIREKTUR:
        return qs
    involved = (Q(created_by=user) | Q(dispositions__to_user=user)
                | Q(dispositions__from_user=user))
    if user.role in (Role.SEKRETARIS, Role.ARSIP, Role.AUDITOR):
        involved |= ~Q(classification=Classification.RAHASIA)
    return qs.filter(involved).distinct()


def can_view_letter(user, letter):
    return visible_letters(user, IncomingLetter.objects.filter(pk=letter.pk)).exists()


def visible_outgoing(user, qs=None):
    qs = OutgoingLetter.objects.all() if qs is None else qs
    if user.role == Role.DIREKTUR:
        return qs
    if user.role in (Role.SEKRETARIS, Role.ARSIP, Role.AUDITOR):
        return qs.filter(~Q(classification=Classification.RAHASIA) | Q(created_by=user))
    return qs.filter(created_by=user)


@transaction.atomic
def register_incoming(user, **fields):
    if not can_register_letter(user):
        raise PermissionDenied
    letter = IncomingLetter(created_by=user, **fields)
    letter.agenda_number = next_number(IncomingLetter, "agenda_number", "SM")
    letter.save()
    audit.log(user, "letter.incoming.create", letter, classification=letter.classification)
    return letter


@transaction.atomic
def register_outgoing(user, **fields):
    if not can_register_letter(user):
        raise PermissionDenied
    letter = OutgoingLetter(created_by=user, **fields)
    letter.letter_number = next_number(OutgoingLetter, "letter_number", "SK")
    letter.save()
    audit.log(user, "letter.outgoing.create", letter, classification=letter.classification)
    return letter


@transaction.atomic
def create_disposition(user, letter, *, parent=None, **fields):
    if not can_dispose(user):
        raise PermissionDenied
    if not can_view_letter(user, letter):
        raise PermissionDenied
    if parent and parent.to_user_id != user.pk:
        raise PermissionDenied
    disp = Disposition(letter=letter, from_user=user, parent=parent, **fields)
    if disp.requires_action and not disp.due_date:
        raise ValidationError({"due_date": "Disposisi yang memerlukan tindakan wajib memiliki tenggat."})
    disp.save()
    audit.log(user, "disposition.create", disp, to_user=disp.to_user, due_date=disp.due_date,
              forwarded_from=parent.pk if parent else None)
    if disp.requires_action:
        workflow.create_task(
            created_by=user,
            title=f"Tindak lanjut {letter.agenda_number}: {letter.subject}"[:255],
            description=disp.directive,
            source_type=TaskSource.DISPOSISI,
            disposition=disp,
            unit=disp.to_unit,
            pic=disp.to_user,
            priority=disp.priority,
            classification=letter.classification,
            due_date=disp.due_date,
            verifier=user,
        )
    notify.disposition_received(disp)
    return disp


def visible_dispositions(user, qs=None):
    qs = Disposition.objects.all() if qs is None else qs
    return qs.filter(letter__in=visible_letters(user)).filter(
        Q(to_user=user) | Q(from_user=user) | Q(pk__in=_all_if_exec(user))
    )


def _all_if_exec(user):
    if user.role == Role.DIREKTUR:
        return Disposition.objects.values("pk")
    if user.role in (Role.SEKRETARIS, Role.AUDITOR):
        return Disposition.objects.exclude(
            letter__classification=Classification.RAHASIA).values("pk")
    return Disposition.objects.none().values("pk")


def mark_read(disposition, user):
    if disposition.to_user_id == user.pk and disposition.status == Disposition.Status.TERKIRIM:
        disposition.status = Disposition.Status.DIBACA
        disposition.read_at = timezone.now()
        disposition.save(update_fields=["status", "read_at"])


def sync_disposition_status(disposition):
    statuses = set(disposition.tasks.values_list("status", flat=True))
    if statuses and statuses <= {TaskStatus.SELESAI, TaskStatus.DIBATALKAN}:
        new = Disposition.Status.SELESAI
    elif statuses - {TaskStatus.MENUNGGU_PENERIMAAN, TaskStatus.DRAF}:
        new = Disposition.Status.DITINDAKLANJUTI
    else:
        return
    if disposition.status != new:
        disposition.status = new
        disposition.save(update_fields=["status"])
