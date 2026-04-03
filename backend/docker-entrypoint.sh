#!/bin/sh
set -eu

log() { printf "\033[1;34m[entrypoint]\033[0m %s\n" "$*"; }

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
    python - <<'PY'
import os
import time

import psycopg

dsn = os.environ["DATABASE_URL"]
for _ in range(60):
    try:
        with psycopg.connect(dsn, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        print("[entrypoint] PostgreSQL is ready.")
        break
    except Exception:
        time.sleep(1)
else:
    raise SystemExit("[entrypoint] PostgreSQL is not ready after 60s")
PY
  fi
}

django_bootstrap() {
  if [ "${DJANGO_CHECK_DEPLOY:-1}" = "1" ]; then
    log "Django check --deploy ..."
    if ! python manage.py check --deploy; then
      if [ "${DJANGO_CHECK_DEPLOY_STRICT:-0}" = "1" ]; then
        log "Django check --deploy failed in strict mode"
        exit 1
      fi
      log "Django check --deploy reported issues (strict mode disabled)"
    fi
  fi

  if [ "${DJANGO_MIGRATE:-1}" = "1" ]; then
    log "Applying migrations ..."
    python manage.py migrate --noinput
  fi

  if [ "${DJANGO_SYNC_SITE:-1}" = "1" ]; then
    log "Ensuring django.contrib.sites is configured ..."
    python manage.py sync_site
  fi

  if [ "${DJANGO_SYNC_EMAIL_ADDRESSES:-1}" = "1" ]; then
    log "Syncing allauth email addresses ..."
    python manage.py sync_email_addresses
  fi

  if [ "${DJANGO_COLLECTSTATIC:-1}" = "1" ]; then
    log "Collecting static ..."
    python manage.py collectstatic --noinput
  fi

  if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_EMAIL:-}" ] ; then
  log "Ensuring superuser ${DJANGO_SUPERUSER_USERNAME} exists ..."
  python manage.py shell -c "
import os
from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist

User = get_user_model()
username_field = User.USERNAME_FIELD

u = os.environ['DJANGO_SUPERUSER_USERNAME']
e = os.environ['DJANGO_SUPERUSER_EMAIL']
p = os.environ.get('DJANGO_SUPERUSER_PASSWORD') or ''

lookup = {username_field: u}
defaults = {'is_superuser': True, 'is_staff': True}
try:
    User._meta.get_field('email')
except FieldDoesNotExist:
    pass
else:
    defaults['email'] = e

user, created = User.objects.get_or_create(defaults=defaults, **lookup)
if created:
    if p:
        user.set_password(p)
    else:
        user.set_unusable_password()
    user.save()
    print('Created superuser:', getattr(user, username_field))
else:
    print('Superuser already exists:', getattr(user, username_field))
"
fi
}

is_positive_int() {
  case "${1:-}" in
    ''|*[!0-9]*) return 1 ;;
    *) [ "$1" -gt 0 ] ;;
  esac
}

run_auth_maintenance() {
  if python manage.py run_auth_maintenance; then
    return 0
  fi
  if [ "${AUTH_MAINTENANCE_STRICT:-0}" = "1" ]; then
    log "Auth maintenance failed in strict mode"
    exit 1
  fi
  log "Auth maintenance failed (strict mode disabled)"
  return 1
}

start_auth_maintenance_loop() {
  interval_minutes="${AUTH_MAINTENANCE_INTERVAL_MINUTES:-0}"
  if ! is_positive_int "$interval_minutes"; then
    return 0
  fi

  interval_seconds=$((interval_minutes * 60))
  log "Starting auth maintenance loop (every ${interval_minutes}m)"
  (
    while true; do
      sleep "$interval_seconds"
      log "Running scheduled auth maintenance ..."
      python manage.py run_auth_maintenance || true
    done
  ) &
}

wait_for_db
django_bootstrap

if [ "${AUTH_MAINTENANCE_ON_START:-1}" = "1" ]; then
  run_auth_maintenance || true
fi
start_auth_maintenance_loop

log "Starting app: $*"
exec "$@"
