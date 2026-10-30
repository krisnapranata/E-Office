# Image produksi E-Office. Aplikasi dilayani Gunicorn pada port 8090.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod \
    PORT=8090

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --home /app app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY --chown=app:app . .

# collectstatic tidak membutuhkan database; SECRET_KEY di sini hanya untuk tahap build.
RUN DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput \
    && mkdir -p /app/media && chown app:app /app && chown -R app:app /app/media /app/staticfiles \
    && chmod +x /app/docker/entrypoint.sh

USER app
EXPOSE 8090

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8090\")}/healthz', timeout=4)"

ENTRYPOINT ["/app/docker/entrypoint.sh"]
# Peran container: web | worker | beat (lihat docker/entrypoint.sh)
CMD ["web"]
