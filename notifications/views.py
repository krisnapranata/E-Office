from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST


@login_required
def notification_list(request):
    page = Paginator(request.user.notifications.all(), 25).get_page(request.GET.get("page"))
    return render(request, "notifications/list.html", {"page": page})


@login_required
@require_POST
def open_notification(request, pk):
    n = get_object_or_404(request.user.notifications, pk=pk)
    if not n.read_at:
        n.read_at = timezone.now()
        n.save(update_fields=["read_at"])
    url = n.url if url_has_allowed_host_and_scheme(n.url, allowed_hosts=None) else "/"
    return redirect(url or "notifications:list")


@login_required
@require_POST
def mark_all_read(request):
    request.user.notifications.filter(read_at=None).update(read_at=timezone.now())
    return redirect("notifications:list")


@login_required
def badge(request):
    return render(request, "notifications/_badge.html",
                  {"unread_notification_count": request.user.notifications.filter(read_at=None).count()})
