"""Lingkup data tugas per pengguna. Dipakai oleh list, detail, unduhan, dashboard, dan laporan."""
from django.db.models import Q

from accounts.models import Role
from accounts.permissions import Classification, managed_unit_ids

from .models import Task


def _involved(user):
    return (
        Q(pic=user)
        | Q(collaborators=user)
        | Q(created_by=user)
        | Q(verifier=user)
    )


def visible_tasks(user, qs=None):
    qs = Task.objects.all() if qs is None else qs
    if not user.is_authenticated:
        return qs.none()
    if user.role == Role.DIREKTUR:
        return qs
    not_secret = ~Q(classification=Classification.RAHASIA)
    if user.role == Role.AUDITOR:
        return qs.filter(not_secret)
    cond = _involved(user)
    units = managed_unit_ids(user)
    if units:
        cond |= Q(unit_id__in=units) & not_secret
    return qs.filter(cond).distinct()


def can_view_task(user, task):
    return visible_tasks(user, Task.objects.filter(pk=task.pk)).exists()


def is_pic(user, task):
    return task.pic_id == user.pk


def can_report_progress(user, task):
    return user.pk == task.pic_id or task.collaborators.filter(pk=user.pk).exists()


def can_manage_task(user, task):
    """Mengubah PIC/tenggat, membatalkan, meminta pembaruan."""
    if user.role == Role.AUDITOR:
        return False
    if user.role == Role.DIREKTUR or user.pk in (task.created_by_id, task.verifier_id):
        return True
    return task.unit_id in managed_unit_ids(user) and user.pk != task.pic_id


def can_verify(user, task):
    return user.pk == task.verifier_id
