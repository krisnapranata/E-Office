from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.files import respons_berkas
from accounts.permissions import can_issue_instruction, require
from arsip import services as arsip_services
from audit import services as audit

from . import services
from .forms import InstructionForm, TargetForm
from .models import Instruction, InstructionTarget


@login_required
def instruction_list(request):
    qs = services.visible_instructions(request.user).prefetch_related("targets")
    status = request.GET.get("status")
    if status:
        qs = qs.filter(status=status)
    if request.GET.get("unread"):
        qs = qs.filter(targets__read_at=None).distinct()
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    return render(request, "instructions/list.html", {
        "page": page, "can_create": can_issue_instruction(request.user),
        "statuses": Instruction.Status})


@login_required
def instruction_create(request):
    require(can_issue_instruction(request.user))
    form = InstructionForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        ins = services.create_instruction(request.user, **form.cleaned_data)
        messages.success(request, "Draf instruksi tersimpan. Tambahkan penerima lalu terbitkan.")
        return redirect("instructions:detail", ins.pk)
    return render(request, "instructions/form.html", {"form": form, "title": "Instruksi baru"})


def _get(request, pk):
    ins = get_object_or_404(Instruction, pk=pk)
    if not services.can_view_instruction(request.user, ins):
        raise Http404
    return ins


@login_required
def instruction_edit(request, pk):
    ins = _get(request, pk)
    require(services.can_edit_instruction(request.user, ins))
    form = InstructionForm(request.POST or None, request.FILES or None, instance=ins)
    if request.method == "POST" and form.is_valid():
        form.save()
        audit.log(request.user, "instruction.edit_draft", ins)
        arsip_services.arsipkan_instruksi(ins)      # lampiran baru = versi arsip baru
        return redirect("instructions:detail", ins.pk)
    return render(request, "instructions/form.html", {"form": form, "title": f"Ubah {ins.code}"})


@login_required
def instruction_detail(request, pk):
    ins = _get(request, pk)
    services.mark_read(ins, request.user)
    editable = services.can_edit_instruction(request.user, ins)
    return render(request, "instructions/detail.html", {
        "ins": ins,
        "targets": ins.targets.select_related("unit", "pic"),
        "tasks": ins.tasks.select_related("pic", "unit"),
        "editable": editable,
        "target_form": TargetForm() if editable else None,
        "can_cancel": ins.status != Instruction.Status.DIBATALKAN and (
            request.user.pk in (ins.created_by_id, ins.on_behalf_of_id)
            or request.user.role == "DIREKTUR"),
    })


@login_required
@require_POST
def target_add(request, pk):
    ins = _get(request, pk)
    require(services.can_edit_instruction(request.user, ins))
    form = TargetForm(request.POST)
    if form.is_valid():
        InstructionTarget.objects.get_or_create(instruction=ins, **form.cleaned_data)
    else:
        messages.error(request, "Unit dan PIC wajib dipilih.")
    return redirect("instructions:detail", ins.pk)


@login_required
@require_POST
def target_remove(request, pk, target_pk):
    ins = _get(request, pk)
    require(services.can_edit_instruction(request.user, ins))
    ins.targets.filter(pk=target_pk).delete()
    return redirect("instructions:detail", ins.pk)


@login_required
@require_POST
def instruction_issue(request, pk):
    ins = _get(request, pk)
    try:
        services.issue(ins, request.user)
        messages.success(request, "Instruksi diterbitkan dan tugas dibuat.")
    except ValidationError as e:
        messages.error(request, " ".join(e.messages))
    return redirect("instructions:detail", ins.pk)


@login_required
@require_POST
def instruction_cancel(request, pk):
    ins = _get(request, pk)
    try:
        services.cancel(ins, request.user, request.POST.get("reason", ""))
        messages.success(request, "Instruksi dibatalkan.")
    except ValidationError as e:
        messages.error(request, " ".join(e.messages))
    return redirect("instructions:detail", ins.pk)


@login_required
def attachment_download(request, pk):
    ins = _get(request, pk)
    if not ins.attachment:
        raise Http404
    nama = (f"{ins.code.replace('/', '-')}-lampiran"
            f"{'.' + ins.attachment.name.rsplit('.', 1)[-1] if '.' in ins.attachment.name else ''}")
    r, lihat = respons_berkas(request, ins.attachment, nama)
    audit.log(request.user, "instruction.view" if lihat else "instruction.download", ins)
    return r
