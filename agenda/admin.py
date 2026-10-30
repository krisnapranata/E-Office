from django.contrib import admin

from .models import AgendaEvent, AgendaMaterial


class MaterialInline(admin.TabularInline):
    model = AgendaMaterial
    extra = 0


@admin.register(AgendaEvent)
class AgendaEventAdmin(admin.ModelAdmin):
    list_display = ("start", "title", "kind", "organizer", "status")
    list_filter = ("kind", "status")
    search_fields = ("title",)
    inlines = [MaterialInline]

    def has_delete_permission(self, request, obj=None):
        return False
