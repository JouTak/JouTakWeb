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

wait_for_db
django_bootstrap

log "Starting app: $*"
exec "$@"
