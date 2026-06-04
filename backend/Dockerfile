# syntax=docker/dockerfile:1.7

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH

RUN python -m venv "$VIRTUAL_ENV"

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv export --frozen --no-dev -q -o /tmp/req.lock.txt \
    && uv pip install --python "$VIRTUAL_ENV/bin/python" -r /tmp/req.lock.txt


FROM python:3.12-slim AS runtime

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
