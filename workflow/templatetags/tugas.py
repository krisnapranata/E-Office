from django import template

from workflow.models import TaskStatus

register = template.Library()


@register.filter
def label_status(kode):
    """Kode status (mis. BELUM_DIMULAI) -> label yang dibaca orang (Belum dimulai)."""
    try:
        return TaskStatus(kode).label
    except ValueError:
        return kode


@register.filter
def jabatan(user):
    """Jabatan untuk ditampilkan di samping nama: isian jabatan, atau peran + kode unit bila kosong."""
    if not user:
        return ""
    if user.position:
        return user.position
    return f"{user.get_role_display()}{' ' + user.unit.code if user.unit_id else ''}"
