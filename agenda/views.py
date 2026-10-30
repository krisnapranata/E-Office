import calendar
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.files import respons_berkas
from accounts.permissions import require
from audit import services as audit

from . import services
from .forms import EventForm, MaterialForm
from .models import AgendaEvent, AgendaMaterial


def _get(request, pk):
    ev = get_object_or_404(AgendaEvent.objects.select_related("organizer", "created_by"), pk=pk)
    if not services.can_view_event(request.user, ev):
        raise Http404
    return ev


@login_required
def event_list(request):
    qs = services.visible_events(request.user).select_related("organizer")
    sekarang = timezone.now()
    tampil = request.GET.get("tampil", "mendatang")
    if tampil == "lalu":
        qs = qs.filter(start__lt=sekarang).order_by("-start")
    elif tampil == "semua":
        qs = qs.order_by("-start")
    else:
        hari_ini = timezone.localtime(sekarang).replace(hour=0, minute=0, second=0, microsecond=0)
        qs = qs.filter(start__gte=hari_ini)
    if request.GET.get("jenis"):
        qs = qs.filter(kind=request.GET["jenis"])
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    return render(request, "agenda/list.html", {
        "page": page, "tampil": tampil, "jenis": AgendaEvent.Kind.choices,
        "can_create": services.can_create_event(request.user)})


@login_required
def event_calendar(request):
    try:
        bulan = datetime.strptime(request.GET.get("bulan", ""), "%Y-%m").date()
    except ValueError:
        bulan = timezone.localdate().replace(day=1)
    minggu = calendar.Calendar(firstweekday=0).monthdatescalendar(bulan.year, bulan.month)
    awal, akhir = minggu[0][0], minggu[-1][-1]
    per_hari = {}
    for ev in services.visible_events(request.user).filter(start__date__gte=awal, start__date__lte=akhir):
        per_hari.setdefault(timezone.localtime(ev.start).date(), []).append(ev)
    sebelum = (bulan - timedelta(days=1)).replace(day=1)
    sesudah = (bulan + timedelta(days=32)).replace(day=1)
    return render(request, "agenda/calendar.html", {
        "bulan": bulan, "hari_ini": timezone.localdate(),
        "minggu": [[(d, per_hari.get(d, [])) for d in w] for w in minggu],
        "sebelum": sebelum.strftime("%Y-%m"), "sesudah": sesudah.strftime("%Y-%m"),
        "nama_hari": ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"],
        "can_create": services.can_create_event(request.user)})


@login_required
def event_create(request):
    require(services.can_create_event(request.user))
    awal = {"organizer": request.user}
    if request.GET.get("tanggal"):
        try:
            awal["start"] = datetime.combine(date.fromisoformat(request.GET["tanggal"]), datetime.min.time()).replace(hour=9)
        except ValueError:
            pass
    form = EventForm(request.POST or None, initial=awal)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        peserta = data.pop("participants")
        try:
            ev = services.create_event(request.user, participants=peserta, **data)
        except ValidationError as e:
            form.add_error(None, e)
        else:
            messages.success(request, "Agenda tersimpan dan undangan dikirim.")
            return redirect("agenda:detail", ev.pk)
    return render(request, "agenda/form.html", {"form": form, "title": "Agenda baru"})


@login_required
def event_edit(request, pk):
    ev = _get(request, pk)
    require(services.can_manage_event(request.user, ev) and ev.status == AgendaEvent.Status.TERJADWAL)
    form = EventForm(request.POST or None, instance=ev)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        peserta = data.pop("participants")
        try:
            services.update_event(AgendaEvent.objects.get(pk=ev.pk), request.user, participants=peserta, **data)
        except ValidationError as e:
            form.add_error(None, e)
        else:
            messages.success(request, "Agenda diperbarui.")
            return redirect("agenda:detail", ev.pk)
    return render(request, "agenda/form.html", {"form": form, "title": f"Ubah agenda: {ev.title}"})


@login_required
def event_detail(request, pk):
    ev = _get(request, pk)
    from notulen.services import can_write_minutes

    minutes = getattr(ev, "minutes", None)
    return render(request, "agenda/detail.html", {
        "ev": ev, "peserta": ev.participants.all(), "bahan": ev.materials.select_related("uploaded_by"),
        "minutes": minutes, "kelola": services.can_manage_event(request.user, ev),
        "boleh_bahan": services.can_manage_event(request.user, ev) or ev.participants.filter(pk=request.user.pk).exists(),
        "boleh_notulen": ev.is_meeting and ev.status != AgendaEvent.Status.DIBATALKAN and not minutes
        and can_write_minutes(request.user, ev),
        "material_form": MaterialForm()})


def _aksi(request, pk, fn, sukses):
    ev = _get(request, pk)
    try:
        fn(ev)
        messages.success(request, sukses)
    except ValidationError as e:
        messages.error(request, " ".join(e.messages))
    return redirect("agenda:detail", ev.pk)


@login_required
@require_POST
def event_cancel(request, pk):
    return _aksi(request, pk, lambda ev: services.cancel_event(ev, request.user, request.POST.get("reason", "")),
                 "Agenda dibatalkan dan peserta diberi tahu.")


@login_required
@require_POST
def event_complete(request, pk):
    return _aksi(request, pk, lambda ev: services.complete_event(ev, request.user), "Agenda ditandai selesai.")


@login_required
@require_POST
def material_add(request, pk):
    def run(ev):
        form = MaterialForm(request.POST, request.FILES)
        if not form.is_valid():
            raise ValidationError([v[0] for v in form.errors.values()])
        services.add_material(ev, request.user, form.cleaned_data["file"], form.cleaned_data["description"])
    return _aksi(request, pk, run, "Bahan diunggah.")


@login_required
def material_download(request, pk):
    m = get_object_or_404(AgendaMaterial.objects.select_related("event"), pk=pk)
    if not services.can_view_event(request.user, m.event):
        raise Http404
    r, lihat = respons_berkas(request, m.file, m.original_name)
    audit.log(request.user, "agenda.material.view" if lihat else "agenda.material.download", m.event,
              file=m.original_name)
    return r
