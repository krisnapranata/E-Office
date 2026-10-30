from .base import *  # noqa: F401,F403
from .base import env

DEBUG = True
SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-only-insecure-key-ganti-di-produksi")
CELERY_TASK_ALWAYS_EAGER = True
