from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from accounts.permissions import is_executive
from audit.models import AuditLog

from .services import summary


@login_required
def home(request):
    ctx = summary(request.user)
    if is_executive(request.user):
        ctx["recent_activity"] = AuditLog.objects.select_related("user")[:10]
    return render(request, "dashboard/home.html", ctx)
