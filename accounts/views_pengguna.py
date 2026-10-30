"""Halaman Pengguna: input pegawai per unit/bidang dari Master Organisasi (khusus Administrator)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from audit.models import AuditLog

from . import pengguna as svc
from .forms import PenggunaForm
from .models import OrganizationUnit, Role, User
from .organisasi import can_manage
from .permissions import require


def _kelompok(users):
    """Kelompokkan per bidang (anak langsung unit puncak; unit puncak/komite = kelompok sendiri), urut pohon."""
    units = {u.pk: u for u in OrganizationUnit.objects.all()}
    urutan = {u.pk: i for i, (u, _) in enumerate(svc.pilihan_unit())}

    def bidang(unit):
        jalur, u = [], unit
        while u and u.pk not in {x.pk for x in jalur}:
            jalur.insert(0, u)
            u = units.get(u.parent_id)
        return jalur[1] if len(jalur) > 1 else jalur[0]

    grup = {}
    for p in users:
        b = bidang(units[p.unit_id]) if p.unit_id else None
        grup.setdefault(b.pk if b else None, {"bidang": b, "pengguna": []})["pengguna"].append(p)
    for g in grup.values():
        g["pengguna"].sort(key=lambda p: (urutan.get(p.unit_id, 9999), not p.is_kepala, p.first_name.lower()))
    return sorted(grup.values(), key=lambda g: urutan.get(g["bidang"].pk, 9999) if g["bidang"] else 99999)


@login_required
def index(request):
    require(can_manage(request.user))
    f = {k: request.GET.get(k, "") for k in ("q", "unit", "role", "status")}
    qs = User.objects.select_related("unit", "supervisor").order_by("first_name", "username")
    if f["status"] != "semua":
        qs = qs.filter(is_active=f["status"] != "nonaktif")
    if f["q"]:
        qs = qs.filter(Q(first_name__icontains=f["q"]) | Q(last_name__icontains=f["q"])
                       | Q(username__icontains=f["q"]) | Q(position__icontains=f["q"]))
    if f["unit"].isdigit():
        unit = OrganizationUnit.objects.filter(pk=f["unit"]).first()
        if unit:
            qs = qs.filter(unit_id__in=unit.descendant_ids())
    if f["role"]:
        qs = qs.filter(role=f["role"])
    kepala = set(OrganizationUnit.objects.exclude(head=None).values_list("head_id", "pk"))
    users = list(qs)
    for p in users:
        p.is_kepala = (p.pk, p.unit_id) in kepala
    aktif = OrganizationUnit.objects.filter(is_active=True)
    return render(request, "pengguna/index.html", {
        "grup": _kelompok(users), "total": len(users), "f": f, "roles": Role.choices,
        "opsi_unit": [(u.pk, "\u00a0" * 3 * d + ("· " if d else "") + u.name) for u, d in svc.pilihan_unit()],
        "tanpa_pengguna": aktif.exclude(members__is_active=True).order_by("order", "name"),
        "tanpa_unit": User.objects.filter(is_active=True, unit=None).count()})


def _form(request, user=None):
    pilihan = svc.pilihan_unit(sertakan=user.unit if user else None)
    awal = {}
    if user is None and request.GET.get("unit", "").isdigit():
        awal["unit"] = request.GET["unit"]
    form = PenggunaForm(request.POST or None, instance=user or User(), initial=awal, pilihan=pilihan)
    if request.method == "POST" and form.is_valid():
        cd = form.cleaned_data
        data = {k: cd[k] for k in PenggunaForm.Meta.fields}
        try:
            if user is None:
                hasil, diganti = svc.create_user(request.user, data, cd["password1"], cd["kepala"])
            else:
                hasil, diganti = svc.update_user(request.user, user, data, cd["password1"], cd["kepala"])
        except ValidationError as e:
            if hasattr(e, "error_dict"):
                for field, errs in e.message_dict.items():
                    form.add_error(field if field in form.fields else ("password1" if field == "password" else None),
                                   errs)
            else:
                form.add_error("password1" if user is None or cd["password1"] else None, e)
        else:
            messages.success(request, f"Pengguna {hasil} disimpan di {hasil.unit.name}.")
            if diganti:
                messages.warning(request, f"Kepala unit {hasil.unit.name} sebelumnya ({diganti}) digantikan.")
            if request.POST.get("lagi") and user is None:
                return redirect(f"{request.path}?unit={hasil.unit_id}")
            return redirect("pengguna:edit", hasil.pk)
    return form, pilihan


@login_required
def create(request):
    require(can_manage(request.user))
    hasil = _form(request)
    if not isinstance(hasil, tuple):
        return hasil
    form, pilihan = hasil
    return render(request, "pengguna/form.html", {"form": form, "title": "Tambah pengguna",
                                                  "saran": svc.peta_saran(pilihan)})


@login_required
def edit(request, pk):
    require(can_manage(request.user))
    user = get_object_or_404(User.objects.select_related("unit", "supervisor"), pk=pk)
    require(request.user.is_superuser or not user.is_superuser)
    hasil = _form(request, user)
    if not isinstance(hasil, tuple):
        return hasil
    form, pilihan = hasil
    return render(request, "pengguna/form.html", {
        "form": form, "title": f"Ubah pengguna: {user}", "obj": user, "saran": svc.peta_saran(pilihan),
        "bawahan": user.subordinates.filter(is_active=True).select_related("unit"),
        "audit": AuditLog.objects.filter(object_type="user", object_id=str(user.pk))[:15]})


def _aksi(request, pk, fn):
    user = get_object_or_404(User, pk=pk)
    require(can_manage(request.user))
    try:
        fn(user)
    except ValidationError as e:
        for x in e.messages:
            messages.error(request, x)
    return redirect("pengguna:edit", user.pk)


@login_required
@require_POST
def deactivate(request, pk):
    def run(user):
        dilepas = svc.deactivate(request.user, user)
        messages.success(request, f"{user} dinonaktifkan; tidak bisa login, riwayat tetap utuh."
                         + (f" Jabatan kepala dilepas: {', '.join(dilepas)}." if dilepas else ""))
    return _aksi(request, pk, run)


@login_required
@require_POST
def activate(request, pk):
    def run(user):
        svc.activate(request.user, user)
        messages.success(request, f"{user} diaktifkan kembali.")
    return _aksi(request, pk, run)
