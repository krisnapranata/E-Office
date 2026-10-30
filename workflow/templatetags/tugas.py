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
