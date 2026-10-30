from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.files import buka_berkas
from accounts.permissions import can_assign_task, require
from audit.models import AuditLog
from audit import services as audit

from . import services
from .access import (can_manage_task, can_report_progress, can_verify, can_view_task,
                     visible_tasks)
from .forms import (DirectTaskForm, EvidenceForm, ProgressForm, ReasonForm, ReassignForm,
                    TaskFilterForm, VerifyForm)
from .models import Task, TaskEvidence, TaskSource, TaskStatus


def filter_tasks(user, params):
    """Filter server-side; dipakai oleh daftar monitoring dan tautan angka dashboard."""
    form = TaskFilterForm(params or None)
    qs = visible_tasks(user).select_related("pic", "unit")
    if form.is_valid():
        d = form.cleaned_data
        if d["q"]:
            qs = qs.filter(Q(title__icontains=d["q"]) | Q(description__icontains=d["q"]))
        for field in ("status", "source_type", "priority", "unit", "pic"):
            if d[field]:
                qs = qs.filter(**{field: d[field]})
        if d["flag"] == "overdue":
            qs = qs.overdue()
        elif d["flag"] == "due_soon":
            qs = qs.due_soon()
        elif d["flag"] == "open":
            qs = qs.open()
        if d["due_from"]:
            qs = qs.filter(due_date__gte=d["due_from"])
        if d["due_to"]:
            qs = qs.filter(due_date__lte=d["due_to"])
    return form, qs


@login_required
def task_list(request):
    form, qs = filter_tasks(request.user, request.GET)
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    pic_saya = f"pic={request.user.pk}&"
    tab = [(label, qs) for label, qs in TAB_TUGAS]
    tab.insert(1, ("Tugas saya", pic_saya + "flag=open"))
    sekarang = params.urlencode()
    lanjutan = any(params.get(f) for f in ("source_type", "priority", "unit", "due_from", "due_to")) or (
        params.get("pic") and sekarang not in {qs for _, qs in tab})
    return render(request, "workflow/list.html", {
        "form": form, "page": page, "querystring": sekarang,
        "can_create": can_assign_task(request.user),
        "tab": [(label, qs, qs == sekarang) for label, qs in tab], "filter_lanjutan": lanjutan,
    })


# Tab di atas daftar tugas: bahasa sehari-hari, satu klik = satu filter.
TAB_TUGAS = [
    ("Semua", ""),
    ("Perlu diterima", "status=MENUNGGU_PENERIMAAN"),
    ("Sedang dikerjakan", "status=BERJALAN"),
    ("Terhambat", "status=TERHAMBAT"),
    ("Menunggu diperiksa", "status=MENUNGGU_VERIFIKASI"),
    ("Perlu perbaikan", "status=PERLU_PERBAIKAN"),
    ("Terlambat", "flag=overdue"),
    ("Selesai", "status=SELESAI"),
]


@login_required
def task_create(request):
    require(can_assign_task(request.user))
    form = DirectTaskForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        collaborators = data.pop("collaborators")
        try:
            task = services.create_task(created_by=request.user, source_type=TaskSource.LANGSUNG,
                                        collaborators=collaborators, **data)
        except ValidationError as e:
            form.add_error(None, e)
        else:
            messages.success(request, "Tugas diterbitkan.")
            return redirect("workflow:detail", task.pk)
    return render(request, "workflow/form.html", {"form": form, "title": "Penugasan langsung"})


def _get_task(request, pk):
    task = get_object_or_404(Task.objects.select_related("pic", "unit", "verifier", "created_by"),
                             pk=pk)
    if not can_view_task(request.user, task):
        # 404 agar keberadaan tugas terbatas tidak terungkap lewat tebakan URL.
        raise Http404
    return task


@login_required
def task_detail(request, pk):
    task = _get_task(request, pk)
    user = request.user
    if task.instruction_id and user.pk == task.pic_id:
        # PIC yang membuka tugasnya telah membaca instruksi sumbernya (status baca di E-Instruksi & dashboard).
        from instructions.services import mark_read

        mark_read(task.instruction, user)
    ctx = {
        "task": task,
        "updates": task.updates.select_related("author"),
        "evidences": task.evidences.select_related("uploaded_by"),
        "verifications": task.verifications.select_related("verifier"),
        "audit": AuditLog.objects.filter(object_type="task", object_id=str(task.pk)),
        "is_pic": user.pk == task.pic_id,
        "can_report": can_report_progress(user, task) and not task.is_closed,
        "can_manage": can_manage_task(user, task) and not task.is_closed,
        "can_verify": can_verify(user, task) and task.status == TaskStatus.MENUNGGU_VERIFIKASI,
        "progress_form": ProgressForm(initial={"progress": task.progress,
                                               "status": TaskStatus.BERJALAN}),
        "evidence_form": EvidenceForm(),
        "verify_form": VerifyForm(),
        "reassign_form": ReassignForm(initial={"pic": task.pic, "due_date": task.due_date}),
        "reason_form": ReasonForm(),
        "statuses": TaskStatus,
    }
    ctx["langkah"] = _langkah(task)
    ctx["petunjuk"] = _petunjuk(task, ctx)
    return render(request, "workflow/detail.html", ctx)


def _langkah(task):
    """Tahapan tugas untuk ditampilkan sebagai garis langkah: [(label, 'selesai'|'sekarang'|'nanti')]."""
    S = TaskStatus
    label = ["Diberikan", "Diterima", "Dikerjakan"] + (["Diperiksa"] if task.requires_verification else []) + ["Selesai"]
    posisi = {S.DRAF: 0, S.MENUNGGU_PENERIMAAN: 1, S.BELUM_DIMULAI: 2, S.BERJALAN: 2, S.TERHAMBAT: 2,
              S.PERLU_PERBAIKAN: 2, S.MENUNGGU_VERIFIKASI: 3, S.SELESAI: len(label)}.get(task.status, 0)
    return [(nama, "selesai" if i < posisi else "sekarang" if i == posisi else "nanti") for i, nama in enumerate(label)]


def _petunjuk(task, ctx):
    """Satu kalimat: apa yang harus dilakukan pengguna ini sekarang."""
    S = TaskStatus
    if task.status == S.SELESAI:
        return "Tugas ini sudah selesai."
    if task.status == S.DIBATALKAN:
        return "Tugas ini dibatalkan."
    if ctx["is_pic"]:
        if task.status == S.MENUNGGU_PENERIMAAN:
            return "Tugas ini untuk Anda. Tekan tombol Terima tugas untuk mulai mengerjakan."
        if task.status == S.PERLU_PERBAIKAN:
            return "Hasil Anda dikembalikan. Baca catatan pemeriksa di Riwayat, perbaiki, lalu kirim lagi."
        if task.status == S.MENUNGGU_VERIFIKASI:
            return "Hasil sudah Anda kirim. Tunggu pemeriksaan."
        return ("Kerjakan tugas, laporkan progres secara berkala, unggah bukti, lalu tekan Kirim "
                + ("untuk diperiksa." if task.requires_verification else "untuk menyelesaikan tugas."))
    if ctx["can_verify"]:
        return "Hasil sudah dikirim. Periksa bukti di bawah, lalu setujui atau kembalikan untuk perbaikan."
    if ctx["can_report"]:
        return "Anda ikut mengerjakan tugas ini. Laporkan progres dan unggah bukti bila ada."
    return "Anda dapat memantau perkembangan tugas ini."


def _action(request, pk, fn):
    task = _get_task(request, pk)
    try:
        fn(task)
    except ValidationError as e:
        for msg in e.messages:
            messages.error(request, msg)
    except PermissionDenied:
        raise
    return redirect("workflow:detail", task.pk)


@login_required
@require_POST
def task_accept(request, pk):
    def run(task):
        services.accept_task(task, request.user)
        messages.success(request, "Tugas diterima.")
    return _action(request, pk, run)


@login_required
@require_POST
def task_progress(request, pk):
    def run(task):
        form = ProgressForm(request.POST)
        if not form.is_valid():
            raise ValidationError([f"{k}: {v[0]}" for k, v in form.errors.items()])
        services.report_progress(task, request.user, **form.cleaned_data)
        messages.success(request, "Progres diperbarui.")
    return _action(request, pk, run)


@login_required
@require_POST
def task_evidence(request, pk):
    def run(task):
        form = EvidenceForm(request.POST, request.FILES)
        if not form.is_valid():
            raise ValidationError([v[0] for v in form.errors.values()])
        services.add_evidence(task, request.user, form.cleaned_data["file"],
                              form.cleaned_data["description"])
        messages.success(request, "Bukti diunggah.")
    return _action(request, pk, run)


@login_required
@require_POST
def task_submit(request, pk):
    def run(task):
        services.submit_result(task, request.user, request.POST.get("note", ""))
        messages.success(request, "Hasil dikirim.")
    return _action(request, pk, run)


@login_required
@require_POST
def task_verify(request, pk):
    def run(task):
        form = VerifyForm(request.POST)
        if not form.is_valid():
            raise ValidationError("Keputusan verifikasi tidak valid.")
        services.verify(task, request.user, approved=form.cleaned_data["decision"] == "approve",
                        note=form.cleaned_data["note"])
        messages.success(request, "Verifikasi tersimpan.")
    return _action(request, pk, run)


@login_required
@require_POST
def task_reassign(request, pk):
    def run(task):
        form = ReassignForm(request.POST)
        if not form.is_valid():
            raise ValidationError([v[0] for v in form.errors.values()])
        services.reassign(task, request.user, **form.cleaned_data)
        messages.success(request, "Penugasan diperbarui.")
    return _action(request, pk, run)


@login_required
@require_POST
def task_cancel(request, pk):
    def run(task):
        services.cancel(task, request.user, request.POST.get("reason", ""))
        messages.success(request, "Tugas dibatalkan.")
    return _action(request, pk, run)


@login_required
@require_POST
def task_request_update(request, pk):
    def run(task):
        services.request_update(task, request.user)
        messages.success(request, "Permintaan pembaruan dikirim ke PIC.")
    return _action(request, pk, run)


@login_required
def evidence_download(request, pk):
    ev = get_object_or_404(TaskEvidence.objects.select_related("task"), pk=pk)
    if not can_view_task(request.user, ev.task):
        raise Http404
    audit.log(request.user, "task.evidence.download", ev.task, file=ev.original_name)
    return FileResponse(buka_berkas(ev.file), as_attachment=True, filename=ev.original_name)
