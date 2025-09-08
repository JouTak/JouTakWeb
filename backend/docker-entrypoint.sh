#!/bin/sh
set -euo pipefail

log() { printf "\033[1;34m[entrypoint]\033[0m %s\n" "$*"; }

# --- NEW: найти и перейти в директорию с manage.py ---
APP_DIR="${APP_DIR:-/app}"
if [ -f "$APP_DIR/backend/manage.py" ]; then
  cd "$APP_DIR/backend"
elif [ -f "$APP_DIR/manage.py" ]; then
  cd "$APP_DIR"
else
  log "manage.py not found in $APP_DIR or $APP_DIR/backend"
  ls -la "$APP_DIR" || true
  ls -la "$APP_DIR/backend" || true
  exit 1
fi

wait_for_db() {
  if [ -n "${DATABASE_URL:-}" ] && printf "%s" "$DATABASE_URL" | grep -qE '^postgres(ql)?://'; then
    log "Waiting for PostgreSQL..."
    for i in $(seq 1 60); do
      if pg_isready -d "$DATABASE_URL" >/dev/null 2>&1; then
        log "PostgreSQL is ready."
        return 0
      fi
      sleep 1
    done
    log "PostgreSQL is not ready after 60s"; exit 1
  fi
}

django_bootstrap() {
  if [ "${DJANGO_CHECK_DEPLOY:-1}" = "1" ]; then
    log "Django check --deploy ..."
    python manage.py check --deploy || true
  fi

  if [ "${DJANGO_MIGRATE:-1}" = "1" ]; then
    log "Applying migrations ..."
    python manage.py migrate --noinput
  fi

  if [ "${DJANGO_COLLECTSTATIC:-1}" = "1" ]; then
    log "Collecting static ..."
    python manage.py collectstatic --noinput
  fi

  if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_EMAIL:-}" ] ; then
    log "Creating superuser ${DJANGO_SUPERUSER_USERNAME} (if not exists) ..."
    python - <<'PY'
import os
from django.contrib.auth import get_user_model
User = get_user_model()
u = os.environ["DJANGO_SUPERUSER_USERNAME"]
e = os.environ["DJANGO_SUPERUSER_EMAIL"]
p = os.environ.get("DJANGO_SUPERUSER_PASSWORD","")
if not User.objects.filter(username=u).exists():
    User.objects.create_superuser(username=u, email=e, password=p or None)
PY
  fi
}

wait_for_db
django_bootstrap

log "Starting app: $*"
exec "$@"
