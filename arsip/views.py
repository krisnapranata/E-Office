from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.files import buka_berkas
from accounts.models import Role
from accounts.permissions import require
from audit import services as audit
from audit.models import AuditLog

from . import services
from .forms import ArchiveFilterForm, ArchiveForm, MetadataForm, VersionForm
from .models import ArchiveDocument, ArchiveVersion


def _get(request, pk):
    doc = get_object_or_404(ArchiveDocument.objects.select_related("owner", "unit"), pk=pk)
    if not services.can_view_archive(request.user, doc):
        raise Http404
    return doc


@login_required
def archive_list(request):
    form = ArchiveFilterForm(request.GET or None)
    qs = services.visible_archives(request.user).select_related("unit", "owner")
    if form.is_valid():
        d = form.cleaned_data
        if d["q"]:
            qs = qs.filter(Q(title__icontains=d["q"]) | Q(number__icontains=d["q"]) | Q(keywords__icontains=d["q"]))
        if d["doc_type"]:
            qs = qs.filter(doc_type=d["doc_type"])
        if d["unit"]:
            qs = qs.filter(unit=d["unit"])
        if d["tahun"]:
            qs = qs.filter(doc_date__year=d["tahun"])
        if d["status"] == "RETENSI":
            qs = qs.filter(status=ArchiveDocument.Status.AKTIF, retention_until__lte=timezone.localdate())
        elif d["status"]:
            qs = qs.filter(status=d["status"])
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "arsip/list.html", {"form": form, "page": page, "querystring": params.urlencode(),
                                               "can_create": services.can_manage_archive(request.user)})


@login_required
def archive_create(request):
    require(services.can_manage_archive(request.user))
    form = ArchiveForm(request.POST or None, request.FILES or None, initial={"doc_date": timezone.localdate()})
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        berkas = data.pop("file")
        doc = services.create_manual(request.user, berkas, **data)
        messages.success(request, "Dokumen diarsipkan.")
        return redirect("arsip:detail", doc.pk)
    return render(request, "arsip/form.html", {"form": form, "title": "Arsipkan dokumen"})


@login_required
def archive_detail(request, pk):
    doc = _get(request, pk)
    u = request.user
    src = doc.source
    tautan = {"letters.IncomingLetter": ("letters:incoming_detail", lambda s: s.pk),
              "instructions.Instruction": ("instructions:detail", lambda s: s.pk),
              "workflow.TaskEvidence": ("workflow:detail", lambda s: s.task_id),
              "agenda.AgendaMaterial": ("agenda:detail", lambda s: s.event_id),
              "notulen.MeetingMinutes": ("notulen:detail", lambda s: s.pk),
              "letters.OutgoingLetter": ("letters:outgoing_list", None)}
    sumber = None
    if src is not None and src._meta.label in tautan:
        from django.urls import reverse

        nama, arg = tautan[src._meta.label]
        sumber = reverse(nama, args=[arg(src)] if arg else [])
    return render(request, "arsip/detail.html", {
        "doc": doc, "versi": doc.versions.select_related("uploaded_by"), "sumber": sumber,
        "audit": AuditLog.objects.filter(object_type="archivedocument", object_id=str(doc.pk))[:20],
        "kelola": services.can_manage_archive(u) and doc.status == ArchiveDocument.Status.AKTIF,
        "boleh_versi": doc.status == ArchiveDocument.Status.AKTIF and not doc.source_id
        and (services.can_manage_archive(u) or doc.owner_id == u.pk),
        "boleh_usul": u.role == Role.ARSIP and doc.status == ArchiveDocument.Status.AKTIF
        and doc.retention_until <= timezone.localdate(),
        "boleh_putus": u.role == Role.DIREKTUR and doc.status == ArchiveDocument.Status.DIUSULKAN,
        "version_form": VersionForm(), "metadata_form": MetadataForm(instance=doc)})


def _aksi(request, doc, fn, sukses):
    try:
        fn()
        messages.success(request, sukses)
    except ValidationError as e:
        for x in e.messages:
            messages.error(request, x)
    return redirect("arsip:detail", doc.pk)


@login_required
@require_POST
def archive_version(request, pk):
    doc = _get(request, pk)
    form = VersionForm(request.POST, request.FILES)
    if not form.is_valid():
        for v in form.errors.values():
            messages.error(request, v[0])
        return redirect("arsip:detail", doc.pk)
    return _aksi(request, doc, lambda: services.add_version(doc, request.user, form.cleaned_data["file"],
                                                             form.cleaned_data["note"]), "Versi baru tersimpan.")


@login_required
@require_POST
def archive_metadata(request, pk):
    doc = _get(request, pk)
    require(services.can_manage_archive(request.user))
    form = MetadataForm(request.POST, instance=ArchiveDocument.objects.get(pk=doc.pk))
    if not form.is_valid():
        for v in form.errors.values():
            messages.error(request, v[0])
        return redirect("arsip:detail", doc.pk)
    data = {k: form.cleaned_data[k] for k in form.Meta.fields}
    return _aksi(request, doc, lambda: services.update_metadata(doc, request.user, **data), "Metadata diperbarui.")


@login_required
@require_POST
def archive_propose(request, pk):
    doc = _get(request, pk)
    return _aksi(request, doc, lambda: services.propose_disposal(doc, request.user, request.POST.get("note", "")),
                 "Usulan pemusnahan dikirim ke Direktur.")


@login_required
@require_POST
def archive_decide(request, pk):
    doc = _get(request, pk)
    setuju = request.POST.get("decision") == "approve"
    return _aksi(request, doc, lambda: services.decide_disposal(doc, request.user, approved=setuju,
                                                                 note=request.POST.get("note", "")),
                 "Pemusnahan disetujui." if setuju else "Usulan pemusnahan ditolak.")


@login_required
def version_download(request, pk):
    v = get_object_or_404(ArchiveVersion.objects.select_related("document"), pk=pk)
    if not services.can_view_archive(request.user, v.document):
        raise Http404
    if v.document.status == ArchiveDocument.Status.DIMUSNAHKAN:
        raise Http404
    audit.log(request.user, "archive.download", v.document, version=v.version)
    return FileResponse(buka_berkas(v.file), as_attachment=True, filename=v.original_name)
