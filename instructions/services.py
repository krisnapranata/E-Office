from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import Role
from accounts.permissions import Classification, can_issue_instruction
from arsip import services as arsip
from audit import services as audit
from config.numbering import next_number
from notifications import services as notify
from workflow import services as workflow
from workflow.models import Task, TaskSource

from .models import Instruction


def visible_instructions(user, qs=None):
    from django.db.models import Q

    qs = Instruction.objects.all() if qs is None else qs
    if user.role == Role.DIREKTUR:
        return qs
    cond = Q(created_by=user) | Q(on_behalf_of=user) | Q(targets__pic=user)
    if user.role == Role.AUDITOR:
        cond |= ~Q(classification=Classification.RAHASIA) & ~Q(status=Instruction.Status.DRAF)
    return qs.filter(cond).distinct()


def can_view_instruction(user, instruction):
    return visible_instructions(user, Instruction.objects.filter(pk=instruction.pk)).exists()


def can_edit_instruction(user, instruction):
    return (instruction.status == Instruction.Status.DRAF
            and user.pk in (instruction.created_by_id, instruction.on_behalf_of_id))


@transaction.atomic
def create_instruction(user, **fields):
    if not can_issue_instruction(user):
        raise PermissionDenied
    ins = Instruction(created_by=user, **fields)
    ins.code = next_number(Instruction, "code", "INS")
    ins.save()
    audit.log(user, "instruction.create", ins)
    arsip.arsipkan_instruksi(ins)
    return ins


@transaction.atomic
def issue(instruction, user):
    """Menerbitkan instruksi dan membuat satu tugas per target (tanpa duplikasi)."""
    instruction = Instruction.objects.select_for_update().get(pk=instruction.pk)
    if not can_edit_instruction(user, instruction):
        raise PermissionDenied
    targets = list(instruction.targets.select_related("unit", "pic"))
    if not targets:
        raise ValidationError("Tentukan minimal satu penerima (unit dan PIC).")
    instruction.status = Instruction.Status.DITERBITKAN
    instruction.issued_at = timezone.now()
    instruction.save()
    for t in targets:
        if Task.objects.filter(instruction=instruction, unit=t.unit, pic=t.pic).exists():
            continue
        workflow.create_task(
            created_by=user,
            title=instruction.title,
            description=instruction.description,
            source_type=TaskSource.INSTRUKSI,
            instruction=instruction,
            unit=t.unit,
            pic=t.pic,
            priority=instruction.priority,
            classification=instruction.classification,
            start_date=instruction.instruction_date,
            due_date=instruction.due_date,
            completion_criteria=instruction.completion_criteria,
            requires_evidence=instruction.requires_evidence,
            requires_verification=instruction.requires_verification,
            verifier=instruction.issuer,
        )
        notify.instruction_issued(instruction, t.pic)
    audit.log(user, "instruction.issue", instruction,
              targets=[str(t) for t in targets], due_date=instruction.due_date)
    return instruction


@transaction.atomic
def cancel(instruction, user, reason):
    if user.pk not in (instruction.created_by_id, instruction.on_behalf_of_id) \
            and user.role != Role.DIREKTUR:
        raise PermissionDenied
    if instruction.status == Instruction.Status.DIBATALKAN:
        return instruction
    if not reason.strip():
        raise ValidationError({"reason": "Alasan pembatalan wajib diisi."})
    instruction.status = Instruction.Status.DIBATALKAN
    instruction.cancelled_reason = reason
    instruction.save()
    for task in instruction.tasks.open():
        workflow._set_status(task, "DIBATALKAN", user)
        task.save()
        workflow.notify.task_closed(task)
    audit.log(user, "instruction.cancel", instruction, reason=reason)
    return instruction


def mark_read(instruction, user):
    instruction.targets.filter(pic=user, read_at=None).update(read_at=timezone.now())
