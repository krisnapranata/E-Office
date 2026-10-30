from .base import *  # noqa: F401,F403
from .base import env, env_bool

DEBUG = False
SECRET_KEY = env("DJANGO_SECRET_KEY", required=True)

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# HTTPS diterminasi di reverse proxy (Nginx); aktifkan setelah TLS tersedia.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", False)
# Healthcheck Docker memanggil http://127.0.0.1/healthz langsung (tanpa proxy/X-Forwarded-Proto); tanpa pengecualian
# ini ia dialihkan ke https, gagal, container web tidak pernah "healthy" dan nginx/worker/beat menunggu selamanya.
SECURE_REDIRECT_EXEMPT = [r"^healthz$"]
SESSION_COOKIE_SECURE = env_bool("DJANGO_SECURE_COOKIES", False)
CSRF_COOKIE_SECURE = env_bool("DJANGO_SECURE_COOKIES", False)
SECURE_CONTENT_TYPE_NOSNIFF = True
