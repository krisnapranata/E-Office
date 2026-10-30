"""E-Follow Up = tampilan atas tugas bersumber keputusan rapat (source KEPUTUSAN_RAPAT).
Tidak ada tabel sendiri: progres, bukti, verifikasi, pengingat memakai mesin tugas yang sama (PRD 6.9)."""
from django.db.models import Count, Q
from django.utils import timezone

from workflow.access import visible_tasks
from workflow.models import CLOSED_STATUSES, TaskSource, TaskStatus


def follow_ups(user):
    return visible_tasks(user).filter(source_type=TaskSource.KEPUTUSAN_RAPAT).select_related(
        "pic", "unit", "decision__minutes__event")


def _hitung(qs, today):
    return dict(
        total=Count("id", distinct=True),
        selesai=Count("id", filter=Q(status=TaskStatus.SELESAI), distinct=True),
        terbuka=Count("id", filter=~Q(status__in=CLOSED_STATUSES), distinct=True),
        terlambat=Count("id", filter=Q(due_date__lt=today) & ~Q(status__in=CLOSED_STATUSES), distinct=True),
    )


def per_rapat(qs, today=None):
    today = today or timezone.localdate()
    return (qs.values("decision__minutes__event_id", "decision__minutes__event__title",
                      "decision__minutes__event__start")
            .annotate(**_hitung(qs, today)).order_by("-decision__minutes__event__start"))


def per_unit(qs, today=None):
    today = today or timezone.localdate()
    return qs.values("unit_id", "unit__code", "unit__name").annotate(**_hitung(qs, today)).order_by("unit__code")
