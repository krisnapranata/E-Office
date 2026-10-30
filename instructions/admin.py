from django.contrib import admin

from .models import Instruction, InstructionTarget


class TargetInline(admin.TabularInline):
    model = InstructionTarget
    extra = 0


@admin.register(Instruction)
class InstructionAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "status", "priority", "due_date", "created_by")
    list_filter = ("status", "priority")
    inlines = [TargetInline]
    readonly_fields = ("status", "issued_at")

    def has_delete_permission(self, request, obj=None):
        return False
