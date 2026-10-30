from django.contrib import admin

from .models import DecisionAssignee, MeetingDecision, MeetingMinutes


class DecisionInline(admin.TabularInline):
    model = MeetingDecision
    extra = 0


@admin.register(MeetingMinutes)
class MeetingMinutesAdmin(admin.ModelAdmin):
    list_display = ("event", "status", "revision", "created_by", "approved_at")
    list_filter = ("status",)
    inlines = [DecisionInline]
    readonly_fields = ("status", "revision", "approved_by", "approved_at")

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(DecisionAssignee)
