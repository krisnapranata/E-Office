from django.contrib import admin

from .models import ArchiveDocument, ArchiveVersion


class VersionInline(admin.TabularInline):
    model = ArchiveVersion
    extra = 0
    readonly_fields = ("version", "file", "original_name", "note", "uploaded_by", "uploaded_at")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ArchiveDocument)
class ArchiveDocumentAdmin(admin.ModelAdmin):
    list_display = ("doc_date", "doc_type", "number", "title", "classification", "status", "retention_until")
    list_filter = ("doc_type", "status", "classification")
    search_fields = ("title", "number", "keywords")
    inlines = [VersionInline]
    readonly_fields = ("status", "source_type", "source_id", "disposal_proposed_by", "disposal_approved_by", "disposed_at")

    def has_delete_permission(self, request, obj=None):
        return False
