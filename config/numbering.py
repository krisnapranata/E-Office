"""Penomoran otomatis. Pola dapat disesuaikan setelah format resmi divalidasi (PRD 16 no. 11)."""
from django.utils import timezone


def next_number(model, field, prefix):
    year = timezone.localdate().year
    stem = f"{prefix}/{year}/"
    last = (
        model.objects.filter(**{f"{field}__startswith": stem})
        .order_by(f"-{field}")
        .values_list(field, flat=True)
        .first()
    )
    seq = int(last.rsplit("/", 1)[1]) + 1 if last else 1
    return f"{stem}{seq:04d}"
