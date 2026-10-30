"""Halaman Master Organisasi: pohon unit struktural + hubungan koordinasi/pengawasan."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from audit.models import AuditLog

from . import organisasi as org
from .forms import ReasonForm, RelationForm, UnitForm
from .models import OrganizationRelation, OrganizationUnit
from .permissions import require

NON_STRUKTURAL = {OrganizationUnit.Kind.KOMITE, OrganizationUnit.Kind.PENGAWAS}


@login_required
def index(request):
    nonaktif = bool(request.GET.get("nonaktif"))
    akar = org.tree(include_inactive=nonaktif)
    # Akar dikelompokkan untuk tampilan: garis komando vs unit non-struktural (komite/SPI/unit tanpa induk & tanpa bawahan)
    struktural = [s for s in akar if s["children"] or s["unit"].kind == OrganizationUnit.Kind.DIREKSI]
    struktural.sort(key=lambda s: s["unit"].kind != OrganizationUnit.Kind.DIREKSI)     # pimpinan tampil di atas
    lainnya = [s for s in akar if s not in struktural]
    q = OrganizationUnit.objects
    return render(request, "organisasi/index.html", {
        "struktural": struktural, "nonstruktural": lainnya, "nonaktif": nonaktif,
        "kelola": org.can_manage(request.user),
        "jumlah": {"aktif": q.filter(is_active=True).count(), "nonaktif": q.filter(is_active=False).count(),
                   "relasi": OrganizationRelation.objects.count()},
        "jenis": OrganizationUnit.Kind.choices})


def _form_simpan(request, form, fn, sukses):
    if request.method == "POST" and form.is_valid():
        try:
            unit = fn({k: form.cleaned_data[k] for k in form.Meta.fields})
        except ValidationError as e:
            if hasattr(e, "error_dict"):
                for field, errs in e.message_dict.items():
                    form.add_error(field if field in form.fields else None, errs)
            else:
                form.add_error(None, e)
        else:
            messages.success(request, sukses)
            return unit
    return None


@login_required
def unit_create(request):
    require(org.can_manage(request.user))
    awal = {}
    if request.GET.get("induk"):
        awal["parent"] = OrganizationUnit.objects.filter(pk=request.GET["induk"], is_active=True).first()
    form = UnitForm(request.POST or None, initial=awal)
    unit = _form_simpan(request, form, lambda d: org.create_unit(request.user, **d), "Unit ditambahkan.")
    if unit:
        return redirect("organisasi:edit", unit.pk)
    return render(request, "organisasi/form.html", {"form": form, "title": "Tambah unit organisasi"})


@login_required
def unit_edit(request, pk):
    unit = get_object_or_404(OrganizationUnit.objects.select_related("parent", "head"), pk=pk)
    kelola = org.can_manage(request.user)
    if request.method == "POST":
        require(kelola)
    form = UnitForm(request.POST or None, instance=OrganizationUnit.objects.get(pk=pk))
    if _form_simpan(request, form, lambda d: org.update_unit(unit, request.user, **d), "Unit diperbarui."):
        return redirect("organisasi:edit", unit.pk)
    return render(request, "organisasi/edit.html", {
        "unit": unit, "form": form, "kelola": kelola,
        "jalur": _jalur(unit), "anak": unit.children.order_by("order", "name"),
        "relasi_keluar": unit.relations_out.select_related("target"),
        "relasi_masuk": unit.relations_in.select_related("unit"),
        "anggota": unit.members.filter(is_active=True).count(),
        "daftar_anggota": unit.members.filter(is_active=True).order_by("first_name", "username"),
        "audit": AuditLog.objects.filter(object_type="organizationunit", object_id=str(unit.pk))[:15],
        "relation_form": RelationForm(), "reason_form": ReasonForm()})


def _jalur(unit):
    jalur, u, lihat = [], unit.parent, set()
    while u and u.pk not in lihat:
        lihat.add(u.pk)
        jalur.insert(0, u)
        u = u.parent
    return jalur


def _aksi(request, pk, fn, sukses):
    unit = get_object_or_404(OrganizationUnit, pk=pk)
    require(org.can_manage(request.user))
    try:
        fn(unit)
        messages.success(request, sukses)
    except ValidationError as e:
        for x in e.messages:
            messages.error(request, x)
    return redirect("organisasi:edit", unit.pk)


@login_required
@require_POST
def unit_deactivate(request, pk):
    return _aksi(request, pk, lambda u: org.deactivate(u, request.user, request.POST.get("reason", "")),
                 "Unit dinonaktifkan. Data lama yang merujuk unit ini tetap utuh.")


@login_required
@require_POST
def unit_activate(request, pk):
    return _aksi(request, pk, lambda u: org.activate(u, request.user), "Unit diaktifkan kembali.")


@login_required
@require_POST
def relation_add(request, pk):
    def run(unit):
        form = RelationForm(request.POST)
        if not form.is_valid():
            raise ValidationError("Pilih unit tujuan dan jenis hubungan.")
        org.add_relation(request.user, unit, **form.cleaned_data)
    return _aksi(request, pk, run, "Hubungan ditambahkan.")


@login_required
@require_POST
def relation_remove(request, pk, rel_pk):
    rel = get_object_or_404(OrganizationRelation, pk=rel_pk, unit_id=pk)
    return _aksi(request, pk, lambda u: org.remove_relation(request.user, rel), "Hubungan dihapus.")
