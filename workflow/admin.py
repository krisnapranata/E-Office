from django.contrib import admin

from .models import Task, TaskEvidence, TaskUpdate, TaskVerification


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "source_type", "unit", "pic", "status", "due_date")
    list_filter = ("status", "source_type", "priority", "unit")
    search_fields = ("title",)
    readonly_fields = ("status", "progress", "created_by", "closed_at", "submitted_at")

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register([TaskUpdate, TaskVerification])


@admin.register(TaskEvidence)
class TaskEvidenceAdmin(admin.ModelAdmin):
    list_display = ("original_name", "task", "uploaded_by", "uploaded_at")

    def has_delete_permission(self, request, obj=None):
        return False
