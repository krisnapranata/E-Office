from datetime import timedelta

from django.db.models import Count, F, Q
from django.utils import timezone

from instructions.models import Instruction, InstructionTarget
from instructions.services import visible_instructions
from letters.models import Disposition
from letters.services import visible_dispositions
from workflow.access import visible_tasks
from workflow.models import CLOSED_STATUSES, TaskStatus


def summary(user, today=None):
    """Seluruh angka dihitung dari lingkup data pengguna, sehingga konsisten dengan daftar detail."""
    today = today or timezone.localdate()
    tasks = visible_tasks(user)
    S = TaskStatus
    by_status = dict(tasks.values_list("status").annotate(n=Count("id", distinct=True)))
    instructions = visible_instructions(user)
    return {
        "today": today,
        "cards": [
            ("Belum dimulai", by_status.get(S.BELUM_DIMULAI, 0) + by_status.get(S.MENUNGGU_PENERIMAAN, 0),
             "flag=open&status=BELUM_DIMULAI", "secondary"),
            ("Berjalan", by_status.get(S.BERJALAN, 0), "status=BERJALAN", "primary"),
            ("Tenggat ≤ H-2", tasks.due_soon(today).count(), "flag=due_soon", "warning"),
            ("Terlambat", tasks.overdue(today).count(), "flag=overdue", "danger"),
            ("Terhambat", by_status.get(S.TERHAMBAT, 0), "status=TERHAMBAT", "danger"),
            ("Menunggu verifikasi", by_status.get(S.MENUNGGU_VERIFIKASI, 0),
             "status=MENUNGGU_VERIFIKASI", "info"),
            ("Perlu perbaikan", by_status.get(S.PERLU_PERBAIKAN, 0), "status=PERLU_PERBAIKAN",
             "warning"),
            ("Selesai", by_status.get(S.SELESAI, 0), "status=SELESAI", "success"),
        ],
        "active_instructions": instructions.filter(status=Instruction.Status.DITERBITKAN)
        .filter(tasks__status__in=[s for s in S.values if s not in CLOSED_STATUSES]).distinct().count(),
        "unread_instructions": InstructionTarget.objects.filter(
            instruction__in=instructions.filter(status=Instruction.Status.DITERBITKAN),
            read_at=None).values("instruction").distinct().count(),
        "pending_dispositions": visible_dispositions(user).exclude(
            status=Disposition.Status.SELESAI).count(),
        "units": unit_performance(tasks, today),
        **agenda_dan_tindak_lanjut(user, tasks, today),
        "trend": completion_trend(tasks, today),
        "blocked": tasks.filter(status=S.TERHAMBAT).select_related("pic", "unit")[:5],
        "overdue": tasks.overdue(today).select_related("pic", "unit").order_by("due_date")[:10],
    }


def unit_performance(tasks, today):
    rows = (
        tasks.values("unit_id", "unit__code", "unit__name")
        .annotate(
            total=Count("id", distinct=True),
            done=Count("id", filter=Q(status=TaskStatus.SELESAI), distinct=True),
            on_time=Count("id", filter=Q(status=TaskStatus.SELESAI, due_date__isnull=False,
                                         submitted_at__date__lte=F("due_date")), distinct=True),
            overdue=Count("id", filter=Q(due_date__lt=today) & ~Q(status__in=CLOSED_STATUSES),
                          distinct=True),
        )
        .order_by("unit__code")
    )
    result = []
    for r in rows:
        r["on_time_pct"] = round(100 * r["on_time"] / r["done"]) if r["done"] else None
        result.append(r)
    return result


def completion_trend(tasks, today, weeks=6):
    start = today - timedelta(days=today.weekday()) - timedelta(weeks=weeks - 1)
    result = []
    for i in range(weeks):
        wk = start + timedelta(weeks=i)
        n = tasks.filter(status=TaskStatus.SELESAI, closed_at__date__gte=wk,
                         closed_at__date__lt=wk + timedelta(days=7)).count()
        result.append({"week": wk, "done": n})
    peak = max((r["done"] for r in result), default=0) or 1
    for r in result:
        r["pct"] = round(100 * r["done"] / peak)
    return result


def agenda_dan_tindak_lanjut(user, tasks, today):
    from agenda.models import AgendaEvent
    from agenda.services import visible_events
    from workflow.models import TaskSource

    # agenda hari ini tetap tampil walau sudah selesai (mis. rapat yang notulennya disetujui); yang batal tidak
    acara = visible_events(user).exclude(status=AgendaEvent.Status.DIBATALKAN).select_related("organizer")
    tl = tasks.filter(source_type=TaskSource.KEPUTUSAN_RAPAT)
    return {
        "agenda_hari_ini": acara.filter(start__date=today).order_by("start")[:8],
        "agenda_mendatang": acara.filter(status=AgendaEvent.Status.TERJADWAL, start__date__gt=today, start__date__lte=today + timedelta(days=7))
        .order_by("start")[:6],
        "tl_terbuka": tl.open().count(),
        "tl_terlambat": tl.overdue(today).count(),
    }
