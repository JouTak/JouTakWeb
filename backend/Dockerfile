FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates tini \
      postgresql-client \
      gcc build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
 && ln -sf /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --python 3.12

ENV PATH="/app/.venv/bin:${PATH}"

COPY . .

RUN useradd -u 10001 -m appuser \
 && chown -R appuser:appuser /app
USER appuser

ENV DJANGO_SETTINGS_MODULE=backend.settings.prod \
    GUNICORN_WORKERS=3 \
    GUNICORN_THREADS=2 \
    GUNICORN_TIMEOUT=60 \
    GUNICORN_BIND=0.0.0.0:8000 \
    HEALTHCHECK_URL=http://127.0.0.1:8000/health

ENTRYPOINT ["/usr/bin/tini","--"]

HEALTHCHECK --interval=20s --timeout=3s --retries=6 \
  CMD /bin/sh -c 'curl -fsS "${http://127.0.0.1:8000/health}" >/dev/null || exit 1'

CMD ["bash","-lc","exec gunicorn backend.wsgi:application \
  --workers ${GUNICORN_WORKERS} \
  --threads ${GUNICORN_THREADS} \
  --timeout ${GUNICORN_TIMEOUT} \
  --bind ${GUNICORN_BIND} \
  --access-logfile - --error-logfile -"]
