from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from accounts.models import Role
from accounts.permissions import can_assign_task, can_issue_instruction, can_register_letter, is_executive
from agenda.services import can_create_event
from audit.models import AuditLog

from .services import beranda, summary


@login_required
def home(request):
    user = request.user
    ctx = summary(user)
    ctx.update(beranda(user, ctx["today"]))
    jam = timezone.localtime().hour
    ctx["salam"] = "Selamat pagi" if jam < 11 else "Selamat siang" if jam < 15 else "Selamat sore" if jam < 18 else "Selamat malam"
    ctx["aksi"] = [a for a in (
        (can_assign_task(user), "workflow:create", "bi-check2-square", "Beri tugas"),
        (can_issue_instruction(user), "instructions:create", "bi-megaphone", "Buat instruksi"),
        (can_register_letter(user), "letters:incoming_create", "bi-envelope-plus", "Catat surat masuk"),
        (can_create_event(user), "agenda:create", "bi-calendar-plus", "Buat agenda"),
    ) if a[0]]
    # Pantauan (kinerja unit, tren, terlambat) hanya untuk yang mengawasi orang lain.
    ctx["pantau"] = is_executive(user) or user.role in (Role.WADIR, Role.KEPALA_UNIT)
    if is_executive(user):
        ctx["recent_activity"] = AuditLog.objects.select_related("user")[:10]
    return render(request, "dashboard/home.html", ctx)
