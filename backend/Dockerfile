# syntax=docker/dockerfile:1.7

FROM python:3.14-slim@sha256:cae66f2ef0ec51a9891263eeee7f987dacf0a9879e8aa9353d5606e0530619a5 AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --python 3.12 --no-dev --no-install-project


FROM python:3.14-slim@sha256:cae66f2ef0ec51a9891263eeee7f987dacf0a9879e8aa9353d5606e0530619a5 AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    DJANGO_SETTINGS_MODULE=backend.settings.prod \
    GUNICORN_CMD_ARGS=--workers=3\ --threads=2\ --timeout=60\ --bind=0.0.0.0:8000\ --access-logfile=-\ --error-logfile=-

RUN apt-get update && apt-get install -y --no-install-recommends \
      libpq5 \
      tini \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 10001 appgroup \
    && useradd --system --uid 10001 --gid appgroup \
       --create-home --home-dir /home/appuser \
       --shell /usr/sbin/nologin appuser

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY backend/ ./backend/
COPY backend/docker-entrypoint.sh /entrypoint.sh

RUN chmod 0755 /entrypoint.sh \
    && mkdir -p /app/media /app/staticfiles \
    && chown -R appuser:appgroup /app

USER appuser

ENTRYPOINT ["/usr/bin/tini", "--", "/entrypoint.sh"]

HEALTHCHECK --interval=20s --timeout=3s --retries=6 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"

EXPOSE 8000
CMD ["gunicorn", "backend.wsgi:application", "--chdir", "backend"]
