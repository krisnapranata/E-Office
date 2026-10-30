from datetime import date

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from accounts.models import OrganizationUnit
from agenda.models import AgendaEvent
from agenda.services import can_view_event
from workflow.models import CLOSED_STATUSES, TaskStatus

from . import services


def _tanggal(teks):
    try:
        return date.fromisoformat(teks)
    except (TypeError, ValueError):
        return None


@login_required
def index(request):
    today = timezone.localdate()
    qs = services.follow_ups(request.user)
    g = request.GET
    if g.get("rapat"):
        qs = qs.filter(decision__minutes__event_id=g["rapat"])
    if g.get("unit"):
        qs = qs.filter(unit_id=g["unit"])
    if g.get("status") == "terbuka":
        qs = qs.exclude(status__in=CLOSED_STATUSES)
    elif g.get("status") == "terlambat":
        qs = qs.overdue(today)
    elif g.get("status"):
        qs = qs.filter(status=g["status"])
    dari, sampai = _tanggal(g.get("dari")), _tanggal(g.get("sampai"))
    if dari:
        qs = qs.filter(decision__minutes__event__start__date__gte=dari)
    if sampai:
        qs = qs.filter(decision__minutes__event__start__date__lte=sampai)
    page = Paginator(qs.order_by("due_date", "-id"), 25).get_page(g.get("page"))
    params = g.copy()
    params.pop("page", None)
    return render(request, "tindaklanjut/index.html", {
        "page": page, "querystring": params.urlencode(), "rapat": services.per_rapat(qs, today),
        "unit": services.per_unit(qs, today), "units": OrganizationUnit.objects.filter(is_active=True),
        "statuses": TaskStatus.choices, "f": g, "today": today})


@login_required
def per_meeting(request, event_pk):
    event = get_object_or_404(AgendaEvent, pk=event_pk)
    if not can_view_event(request.user, event):
        raise Http404
    minutes = getattr(event, "minutes", None)
    tugas = services.follow_ups(request.user).filter(decision__minutes__event=event)
    if request.GET.get("belum"):
        tugas = tugas.exclude(status__in=CLOSED_STATUSES)
    keputusan = {}
    for t in tugas.order_by("decision__number", "unit__code"):
        keputusan.setdefault(t.decision, []).append(t)
    return render(request, "tindaklanjut/rapat.html" if not request.GET.get("cetak") else "tindaklanjut/cetak.html",
                  {"event": event, "minutes": minutes, "keputusan": keputusan, "today": timezone.localdate(),
                   "hanya_belum": bool(request.GET.get("belum")), "dicetak": timezone.localtime()})
