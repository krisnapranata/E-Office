def unread_notifications(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    return {"unread_notification_count": user.notifications.filter(read_at=None).count()}
