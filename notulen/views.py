from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.files import buka_berkas
from accounts.permissions import require
from agenda.models import AgendaEvent
from agenda.services import can_view_event
from audit import services as audit

from . import services
from .forms import AssigneeForm, DecisionForm, MinutesForm
from .models import DecisionAssignee, MeetingDecision, MeetingMinutes


def _get(request, pk):
    m = get_object_or_404(MeetingMinutes.objects.select_related("event__organizer", "created_by"), pk=pk)
    if not can_view_event(request.user, m.event):
        raise Http404
    return m


@login_required
def minutes_list(request):
    qs = services.visible_minutes(request.user).select_related("event", "created_by").order_by("-event__start")
    if request.GET.get("status"):
        qs = qs.filter(status=request.GET["status"])
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    return render(request, "notulen/list.html", {"page": page, "statuses": MeetingMinutes.Status})


@login_required
def minutes_create(request, event_pk):
    event = get_object_or_404(AgendaEvent, pk=event_pk)
    if not can_view_event(request.user, event):
        raise Http404
    require(services.can_write_minutes(request.user, event))
    if hasattr(event, "minutes"):
        return redirect("notulen:detail", event.minutes.pk)
    form = MinutesForm(request.POST or None, request.FILES or None, initial={"attendees": event.participants.all()})
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        hadir = data.pop("attendees")
        try:
            m = services.create_minutes(request.user, event, attendees=hadir, **data)
        except ValidationError as e:
            form.add_error(None, e)
        else:
            messages.success(request, "Draf notulen tersimpan. Tambahkan butir keputusan.")
            return redirect("notulen:detail", m.pk)
    return render(request, "notulen/form.html", {"form": form, "title": f"Notulen: {event.title}", "event": event})


@login_required
def minutes_edit(request, pk):
    m = _get(request, pk)
    require(services.can_edit(request.user, m))
    form = MinutesForm(request.POST or None, request.FILES or None, instance=m)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        hadir = data.pop("attendees")
        services.update_minutes(MeetingMinutes.objects.get(pk=m.pk), request.user, attendees=hadir, **data)
        messages.success(request, "Notulen diperbarui.")
        return redirect("notulen:detail", m.pk)
    return render(request, "notulen/form.html", {"form": form, "title": f"Ubah notulen: {m.event.title}", "event": m.event})


@login_required
def minutes_detail(request, pk):
    m = _get(request, pk)
    keputusan = m.decisions.prefetch_related("assignees__unit", "assignees__pic", "tasks__pic")
    return render(request, "notulen/detail.html", {
        "m": m, "keputusan": keputusan, "hadir": m.attendees.all(),
        "boleh_ubah": services.can_edit(request.user, m),
        "boleh_setujui": services.can_approve(request.user, m) and m.status == MeetingMinutes.Status.DIAJUKAN,
        "decision_form": DecisionForm(initial={"requires_action": True}), "assignee_form": AssigneeForm()})


@login_required
def minutes_print(request, pk):
    m = _get(request, pk)
    return render(request, "notulen/print.html", {"m": m, "keputusan": m.decisions.prefetch_related("assignees__pic", "assignees__unit"),
                                                  "hadir": m.attendees.all()})


def _aksi(request, m, fn, sukses):
    try:
        fn()
        messages.success(request, sukses)
    except ValidationError as e:
        for x in e.messages:
            messages.error(request, x)
    return redirect("notulen:detail", m.pk)


@login_required
@require_POST
def decision_add(request, pk):
    m = _get(request, pk)
    form = DecisionForm(request.POST)
    if not form.is_valid():
        for v in form.errors.values():
            messages.error(request, v[0])
        return redirect("notulen:detail", m.pk)
    return _aksi(request, m, lambda: services.add_decision(m, request.user, **form.cleaned_data), "Keputusan ditambahkan.")


@login_required
@require_POST
def decision_remove(request, pk, decision_pk):
    m = _get(request, pk)
    d = get_object_or_404(MeetingDecision, pk=decision_pk, minutes=m)
    return _aksi(request, m, lambda: services.remove_decision(d, request.user), "Keputusan dihapus.")


@login_required
@require_POST
def assignee_add(request, pk, decision_pk):
    m = _get(request, pk)
    d = get_object_or_404(MeetingDecision, pk=decision_pk, minutes=m)
    form = AssigneeForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Unit dan PIC wajib dipilih.")
        return redirect("notulen:detail", m.pk)
    return _aksi(request, m, lambda: services.add_assignee(d, request.user, **form.cleaned_data), "PIC ditambahkan.")


@login_required
@require_POST
def assignee_remove(request, pk, assignee_pk):
    m = _get(request, pk)
    a = get_object_or_404(DecisionAssignee, pk=assignee_pk, decision__minutes=m)
    return _aksi(request, m, lambda: services.remove_assignee(a, request.user), "PIC dihapus.")


@login_required
@require_POST
def minutes_submit(request, pk):
    m = _get(request, pk)
    return _aksi(request, m, lambda: services.submit(m, request.user), "Notulen diajukan untuk persetujuan.")


@login_required
@require_POST
def minutes_return(request, pk):
    m = _get(request, pk)
    return _aksi(request, m, lambda: services.return_minutes(m, request.user, request.POST.get("note", "")),
                 "Notulen dikembalikan ke notulis.")


@login_required
@require_POST
def minutes_approve(request, pk):
    m = _get(request, pk)
    return _aksi(request, m, lambda: services.approve(m, request.user),
                 "Notulen disetujui; tindak lanjut keputusan telah dibuat.")


@login_required
def minutes_attachment(request, pk):
    m = _get(request, pk)
    if not m.attachment:
        raise Http404
    audit.log(request.user, "minutes.download", m)
    return FileResponse(buka_berkas(m.attachment), as_attachment=True,
                        filename=f"notulen-{m.pk}{'.' + m.attachment.name.rsplit('.', 1)[-1] if '.' in m.attachment.name else ''}")



