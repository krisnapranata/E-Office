"""Konfigurasi dasar E-Office. Nilai rahasia selalu dibaca dari environment."""
import os
from pathlib import Path

from celery.schedules import crontab
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def load_dotenv(path):
    """Muat berkas .env sederhana tanpa menimpa variabel environment yang sudah ada."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_dotenv(BASE_DIR / ".env")


def env(name, default=None, required=False):
    value = os.environ.get(name, default)
    if required and not value:
        raise ImproperlyConfigured(f"Environment variable {name} wajib diisi.")
    return value


def env_bool(name, default=False):
    return str(os.environ.get(name, default)).lower() in ("1", "true", "yes", "on")


def env_list(name, default=""):
    return [v.strip() for v in os.environ.get(name, default).split(",") if v.strip()]


SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "audit",
    "letters",
    "instructions",
    "workflow",
    "notifications",
    "dashboard",
    "agenda",
    "notulen",
    "tindaklanjut",
    "arsip",
    "laporan",
    "panduan",
    "pengaturan",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "notifications.context_processors.unread_notifications",
                "pengaturan.context_processors.mode_aplikasi",
                "dashboard.context_processors.menu",
            ],
        },
    },
]


# Mode awal instalasi baru: DEMO = data contoh dimuat otomatis saat container start (sekali saja);
# PRODUKSI = tanpa data contoh. Setelah instalasi, mode diatur dari menu Pengaturan Aplikasi (tersimpan di DB).
EOFFICE_MODE_AWAL = env("EOFFICE_MODE_AWAL", "DEMO").upper()
# Kata sandi akun demo_* (salah satunya Administrator). Tanpa nilai ini data demo TIDAK dimuat otomatis.
EOFFICE_DEMO_PASSWORD = env("EOFFICE_DEMO_PASSWORD", "")


def database_config():
    engine = env("DB_ENGINE", "sqlite")
    if engine == "mysql":
        import pymysql

        pymysql.install_as_MySQLdb()
        return {
            "ENGINE": "django.db.backends.mysql",
            "NAME": env("DB_NAME", "eoffice"),
            "USER": env("DB_USER", "eoffice"),
            "PASSWORD": env("DB_PASSWORD", ""),
            "HOST": env("DB_HOST", "db"),
            "PORT": env("DB_PORT", "3306"),
            "OPTIONS": {"charset": "utf8mb4"},
            "CONN_MAX_AGE": 60,
        }
    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": env("SQLITE_PATH", str(BASE_DIR / "db.sqlite3")),
    }


DATABASES = {"default": database_config()}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard:home"
LOGOUT_REDIRECT_URL = "login"

LANGUAGE_CODE = "id"
TIME_ZONE = env("TIME_ZONE", "Asia/Jakarta")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Dokumen bukti/lampiran disimpan di luar web root dan hanya diunduh lewat view berizin.
MEDIA_ROOT = Path(env("MEDIA_ROOT", str(BASE_DIR / "media")))
UPLOAD_MAX_BYTES = int(env("UPLOAD_MAX_BYTES", str(10 * 1024 * 1024)))
UPLOAD_ALLOWED_EXTENSIONS = env_list(
    "UPLOAD_ALLOWED_EXTENSIONS", "pdf,jpg,jpeg,png,doc,docx,xls,xlsx"
)
DATA_UPLOAD_MAX_MEMORY_SIZE = UPLOAD_MAX_BYTES

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 8 * 60 * 60
X_FRAME_OPTIONS = "DENY"

# Aturan bisnis yang masih menunggu validasi (PRD Bab 16) dibuat dapat dikonfigurasi.
EOFFICE = {
    "INSTRUCTION_ISSUER_ROLES": env_list(
        "EOFFICE_INSTRUCTION_ISSUER_ROLES", "DIREKTUR,WADIR,SEKRETARIS"
    ),
    "REMINDER_DAYS_BEFORE": [int(d) for d in env_list("EOFFICE_REMINDER_DAYS_BEFORE", "2")],
    "ESCALATION_DAYS_OVERDUE": int(env("EOFFICE_ESCALATION_DAYS_OVERDUE", "3")),
    "REMINDER_HOUR": int(env("EOFFICE_REMINDER_HOUR", "7")),
    # Pengingat agenda: H-1 dan hari-H (0) pada jam pengingat harian.
    "AGENDA_REMINDER_DAYS": [int(d) for d in env_list("EOFFICE_AGENDA_REMINDER_DAYS", "1,0")],
    # Retensi arsip (tahun) — menunggu kebijakan RS (PRD 16 no. 10). Per jenis bisa diatur, mis.
    # EOFFICE_RETENTION_YEARS="DEFAULT=5,SURAT_MASUK=10".
    "RETENTION_YEARS": {k.strip(): int(v) for k, v in (
        x.split("=") for x in env_list("EOFFICE_RETENTION_YEARS", "DEFAULT=5"))},
}

# Gunakan DB Redis dan nama antrean khusus agar tidak berbagi antrean dengan aplikasi lain
# di server yang sama (worker hanya mengonsumsi antrean `eoffice`).
CELERY_BROKER_URL = env("CELERY_BROKER_URL", "redis://localhost:6379/5")
CELERY_TASK_DEFAULT_QUEUE = env("CELERY_QUEUE", "eoffice")
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ACKS_LATE = True
CELERY_BEAT_SCHEDULE = {
    "daily-reminders": {
        "task": "notifications.tasks.run_daily_reminders",
        "schedule": crontab(hour=EOFFICE["REMINDER_HOUR"], minute=0),
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
}
