from .models import AuditLog


def log(user, action, obj, **changes):
    """Catat aksi penting. `changes` berisi ringkasan perubahan, mis. pic=("lama", "baru")."""
    return AuditLog.objects.create(
        user=user if user and user.is_authenticated else None,
        action=action,
        object_type=obj._meta.model_name,
        object_id=str(obj.pk),
        object_repr=str(obj)[:255],
        changes={k: _plain(v) for k, v in changes.items()},
    )


def _plain(value):
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)
