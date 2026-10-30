from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import OrganizationRelation, OrganizationUnit, User


@admin.register(OrganizationUnit)
class OrganizationUnitAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "kind", "parent", "head", "is_active")
    list_filter = ("kind", "is_active")
    search_fields = ("code", "name")

    def has_delete_permission(self, request, obj=None):
        return False      # unit dinonaktifkan, bukan dihapus (lihat halaman Master Organisasi)


@admin.register(OrganizationRelation)
class OrganizationRelationAdmin(admin.ModelAdmin):
    list_display = ("unit", "kind", "target", "note")
    list_filter = ("kind",)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "get_full_name", "role", "unit", "supervisor", "is_active")
    list_filter = ("role", "unit", "is_active")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("E-Office", {"fields": ("role", "unit", "supervisor", "position")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("E-Office", {"fields": ("role", "unit", "supervisor", "position")}),
    )
