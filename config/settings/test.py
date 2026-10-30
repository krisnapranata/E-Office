import tempfile

from .base import *  # noqa: F401,F403

SECRET_KEY = "test-only-key"
# Memakai engine yang sama dengan .env; Django membuat database terpisah `test_<DB_NAME>`
# sehingga pengujian tidak pernah menyentuh database development/produksi (PRD 18.5).
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
MEDIA_ROOT = tempfile.mkdtemp(prefix="eoffice-test-media-")
CELERY_TASK_ALWAYS_EAGER = True
CELERY_BROKER_URL = "memory://"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
