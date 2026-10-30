"""Halaman Pengaturan Aplikasi (khusus Administrator): Mode Demo dan Reset data demo."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from accounts.organisasi import can_manage
from accounts.permissions import require
from audit.models import AuditLog

from . import services as svc
from .models import PengaturanAplikasi


@login_required
def index(request):
    require(can_manage(request.user))
    p = PengaturanAplikasi.ambil()
    return render(request, "pengaturan/index.html", {
        "p": p, "ringkasan": svc.ringkasan(), "frasa": svc.FRASA_RESET,
        "akun_demo_saya": svc.is_akun_demo(request.user),
        "riwayat": AuditLog.objects.filter(object_type="pengaturanaplikasi")[:10]})


@login_required
@require_POST
def muat(request):
    require(can_manage(request.user))
    sandi = request.POST.get("password", "")
    try:
        if sandi:
            validate_password(sandi)
        dibuat, alur = svc.muat_demo(request.user, sandi or None)
    except ValidationError as e:
        for m in e.messages:
            messages.error(request, m)
    else:
        messages.success(request, f"Mode Demo aktif. {dibuat} akun demo baru"
                         + ("; data contoh semua alur dimuat." if alur else "; data contoh sudah ada sebelumnya."))
    return redirect("pengaturan:index")


@login_required
@require_POST
def reset(request):
    require(can_manage(request.user))
    try:
        jumlah = svc.reset_demo(request.user, request.POST.get("frasa", ""))
    except ValidationError as e:
        for m in e.messages:
            messages.error(request, m)
    else:
        messages.success(request, "Data demo direset dan Mode Produksi aktif. Pembaruan/build ulang tidak akan "
                         f"memuat data demo lagi. Dihapus: {jumlah['akun demo']} akun demo, {jumlah['tugas']} tugas, "
                         f"{jumlah['surat masuk']} surat masuk, {jumlah['arsip']} arsip.")
    return redirect("pengaturan:index")
