"""Aturan hak akses terpusat. Semua pemeriksaan dilakukan di sisi server (PRD 18.1 no. 10)."""
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db.models import Q

from .models import Role

# Peran yang melihat seluruh data operasional (baca). Auditor hanya baca.
EXECUTIVE_ROLES = {Role.DIREKTUR, Role.AUDITOR}
LETTER_REGISTRAR_ROLES = {Role.SEKRETARIS, Role.ARSIP, Role.DIREKTUR}
DISPOSER_ROLES = {Role.DIREKTUR, Role.WADIR, Role.KEPALA_UNIT}
TASK_ASSIGNER_ROLES = {Role.DIREKTUR, Role.WADIR, Role.KEPALA_UNIT}


class Classification:
    BIASA = "BIASA"
    TERBATAS = "TERBATAS"
    RAHASIA = "RAHASIA"
    CHOICES = [(BIASA, "Biasa"), (TERBATAS, "Terbatas"), (RAHASIA, "Rahasia")]


def is_executive(user):
    return user.is_authenticated and user.role in EXECUTIVE_ROLES


def is_read_only(user):
    return user.role == Role.AUDITOR


def can_issue_instruction(user):
    return user.is_authenticated and user.role in settings.EOFFICE["INSTRUCTION_ISSUER_ROLES"]


def can_register_letter(user):
    return user.is_authenticated and user.role in LETTER_REGISTRAR_ROLES


def can_dispose(user):
    return user.is_authenticated and user.role in DISPOSER_ROLES


def can_assign_task(user):
    return user.is_authenticated and user.role in TASK_ASSIGNER_ROLES


def managed_unit_ids(user):
    """Unit yang berada dalam lingkup pengawasan pengguna (unit sendiri + sub-unit)."""
    if user.role in (Role.WADIR, Role.KEPALA_UNIT) and user.unit_id:
        return user.unit.descendant_ids()
    return set()


def require(condition):
    if not condition:
        raise PermissionDenied
