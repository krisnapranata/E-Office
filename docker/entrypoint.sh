#!/bin/sh
# Titik masuk container E-OFFICE.
#   web    : migrate + data demo (hanya bila Pengaturan Aplikasi = Mode Demo & belum ada), lalu Gunicorn
#   worker : Celery worker antrean $CELERY_QUEUE
#   beat   : Celery beat (pengingat & eskalasi harian)
#   lainnya: diteruskan apa adanya, mis. `docker compose run --rm web python manage.py createsuperuser`
set -e
cd /app

case "${1:-web}" in
  web)
    python manage.py migrate --noinput
    # Data demo dimuat sekali saja; setelah Reset (Mode Produksi) tidak pernah dimuat lagi saat update.
    python manage.py demo_otomatis || echo "PERINGATAN: data demo gagal dimuat; aplikasi tetap dijalankan."
    exec gunicorn config.wsgi:application \
      --bind "0.0.0.0:${PORT:-8090}" \
      --workers "${GUNICORN_WORKERS:-3}" \
      --timeout "${GUNICORN_TIMEOUT:-60}" \
      --access-logfile - \
      --error-logfile -
    ;;
  worker)
    exec celery -A config worker --loglevel=info --concurrency="${CELERY_CONCURRENCY:-2}" -Q "${CELERY_QUEUE:-eoffice}"
    ;;
  beat)
    exec celery -A config beat --loglevel=info --schedule /tmp/celerybeat-schedule
    ;;
  *)
    exec "$@"
    ;;
esac
