from django.contrib import admin

from .models import Notification, ReminderLog


@admin.register(ReminderLog)
class ReminderLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "task", "kind", "days_offset", "recipient", "status", "attempts")
    list_filter = ("kind", "status", "channel")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("created_at", "recipient", "kind", "title", "read_at")
    list_filter = ("kind",)
