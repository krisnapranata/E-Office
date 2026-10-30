from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from accounts.files import respons_berkas
from accounts.permissions import can_dispose, can_register_letter, require
from audit import services as audit

from . import services
from .forms import DispositionForm, IncomingLetterForm, LetterFilterForm, OutgoingLetterForm
from .models import Disposition, IncomingLetter, OutgoingLetter


@login_required
def incoming_list(request):
    form = LetterFilterForm(request.GET or None)
    qs = services.visible_letters(request.user)
    if form.is_valid():
        d = form.cleaned_data
        if d["q"]:
            qs = qs.filter(Q(subject__icontains=d["q"]) | Q(sender__icontains=d["q"])
                           | Q(letter_number__icontains=d["q"])
                           | Q(agenda_number__icontains=d["q"]))
        if d["date_from"]:
            qs = qs.filter(received_date__gte=d["date_from"])
        if d["date_to"]:
            qs = qs.filter(received_date__lte=d["date_to"])
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    return render(request, "letters/incoming_list.html", {
        "form": form, "page": page, "can_create": can_register_letter(request.user)})


@login_required
def incoming_create(request):
    require(can_register_letter(request.user))
    form = IncomingLetterForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        letter = services.register_incoming(request.user, **form.cleaned_data)
        messages.success(request, f"Surat masuk {letter.agenda_number} tercatat.")
        return redirect("letters:incoming_detail", letter.pk)
    return render(request, "letters/form.html", {"form": form, "title": "Catat surat masuk"})


def _get_letter(request, pk):
    letter = get_object_or_404(IncomingLetter, pk=pk)
    if not services.can_view_letter(request.user, letter):
        raise Http404
    return letter


@login_required
def incoming_detail(request, pk):
    letter = _get_letter(request, pk)
    dispositions = services.visible_dispositions(
        request.user, letter.dispositions.select_related("from_user", "to_user", "to_unit"))
    form = None
    if can_dispose(request.user):
        form = DispositionForm(initial={"to_unit": None}, pemberi=request.user)
    return render(request, "letters/incoming_detail.html", {
        "letter": letter, "dispositions": dispositions, "form": form})


@login_required
def disposition_create(request, pk):
    letter = _get_letter(request, pk)
    require(can_dispose(request.user))
    parent = None
    if request.GET.get("parent") or request.POST.get("parent"):
        parent = get_object_or_404(Disposition, pk=request.GET.get("parent") or request.POST["parent"],
                                   letter=letter)
    form = DispositionForm(request.POST or None, pemberi=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            disp = services.create_disposition(request.user, letter, parent=parent,
                                               **form.cleaned_data)
        except ValidationError as e:
            form.add_error(None, e)
        else:
            messages.success(request, "Disposisi dikirim.")
            return redirect("letters:disposition_detail", disp.pk)
    return render(request, "letters/form.html", {
        "form": form, "title": f"Disposisi {letter.agenda_number}", "parent": parent})


@login_required
def disposition_list(request):
    qs = services.visible_dispositions(request.user).select_related(
        "letter", "from_user", "to_user")
    if request.GET.get("pending"):
        qs = qs.exclude(status=Disposition.Status.SELESAI)
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    return render(request, "letters/disposition_list.html", {"page": page})


@login_required
def disposition_detail(request, pk):
    disp = get_object_or_404(Disposition.objects.select_related("letter"), pk=pk)
    if not services.visible_dispositions(request.user, Disposition.objects.filter(pk=pk)).exists():
        raise Http404
    services.mark_read(disp, request.user)
    return render(request, "letters/disposition_detail.html", {
        "disp": disp, "tasks": disp.tasks.all(),
        "can_forward": can_dispose(request.user) and disp.to_user_id == request.user.pk})


@login_required
def outgoing_list(request):
    page = Paginator(services.visible_outgoing(request.user), 25).get_page(request.GET.get("page"))
    return render(request, "letters/outgoing_list.html", {
        "page": page, "can_create": can_register_letter(request.user)})


@login_required
def outgoing_create(request):
    require(can_register_letter(request.user))
    form = OutgoingLetterForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        letter = services.register_outgoing(request.user, **form.cleaned_data)
        messages.success(request, f"Surat keluar {letter.letter_number} tercatat.")
        return redirect("letters:outgoing_list")
    return render(request, "letters/form.html", {"form": form, "title": "Catat surat keluar"})


@login_required
def attachment_download(request, kind, pk):
    if kind == "masuk":
        letter = _get_letter(request, pk)
    elif kind == "keluar":
        letter = get_object_or_404(services.visible_outgoing(request.user), pk=pk)
    else:
        raise Http404
    if not letter.attachment:
        raise Http404
    r, lihat = respons_berkas(request, letter.attachment, f"{letter.pk}-{letter.attachment.name.rsplit('/', 1)[-1]}")
    audit.log(request.user, "letter.view" if lihat else "letter.download", letter)
    return r
