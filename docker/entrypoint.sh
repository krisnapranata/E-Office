#!/bin/sh
set -e
if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  python manage.py migrate --noinput
  # Data demo hanya dimuat bila Pengaturan Aplikasi = Mode Demo dan belum pernah dimuat (aman tiap start/update).
  python manage.py demo_otomatis || echo "PERINGATAN: data demo gagal dimuat; aplikasi tetap dijalankan."
fi
exec "$@"
