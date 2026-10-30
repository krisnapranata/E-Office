from django.contrib import admin

from .models import Disposition, IncomingLetter, OutgoingLetter


@admin.register(IncomingLetter)
class IncomingLetterAdmin(admin.ModelAdmin):
    list_display = ("agenda_number", "letter_number", "sender", "subject", "classification")
    search_fields = ("agenda_number", "letter_number", "subject", "sender")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OutgoingLetter)
class OutgoingLetterAdmin(admin.ModelAdmin):
    list_display = ("letter_number", "recipient", "subject", "classification")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Disposition)
class DispositionAdmin(admin.ModelAdmin):
    list_display = ("id", "letter", "from_user", "to_user", "status", "due_date")
    list_filter = ("status",)

    def has_delete_permission(self, request, obj=None):
        return False
