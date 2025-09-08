FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates tini \
      postgresql-client \
      gcc build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
 && ln -sf /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /app

# манифесты из КОРНЯ
COPY pyproject.toml uv.lock ./

# зависимости из lock (без dev)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv export --frozen --no-dev -o /tmp/req.lock.txt && \
    uv pip install --system -r /tmp/req.lock.txt

# код бекенда
COPY backend/ ./backend/

# unprivileged user
RUN useradd -u 10001 -m appuser && chown -R appuser:appuser /app
USER appuser

ENV DJANGO_SETTINGS_MODULE=backend.settings.prod \
    GUNICORN_WORKERS=3 \
    GUNICORN_THREADS=2 \
    GUNICORN_TIMEOUT=60 \
    GUNICORN_BIND=0.0.0.0:8000 \
    HEALTHCHECK_URL=http://127.0.0.1:8000/health

ENTRYPOINT ["/usr/bin/tini","--"]

HEALTHCHECK --interval=20s --timeout=3s --retries=6 \
  CMD curl -fsS "$HEALTHCHECK_URL" >/dev/null || exit 1

EXPOSE 8000
CMD ["bash","-lc","exec gunicorn backend.wsgi:application \
  --chdir backend \
  --workers ${GUNICORN_WORKERS} \
  --threads ${GUNICORN_THREADS} \
  --timeout ${GUNICORN_TIMEOUT} \
  --bind ${GUNICORN_BIND} \
  --access-logfile - --error-logfile -"]
