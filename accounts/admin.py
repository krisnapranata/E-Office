from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import OrganizationUnit, User


@admin.register(OrganizationUnit)
class OrganizationUnitAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "parent", "head", "is_active")
    search_fields = ("code", "name")


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
