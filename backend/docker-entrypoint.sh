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
    log "Ensuring cache table exists ..."
    python manage.py createcachetable --database default 2>/dev/null || true
  fi

  if [ "${DJANGO_SYNC_SITE:-1}" = "1" ]; then
    log "Ensuring django.contrib.sites is configured ..."
    python manage.py sync_site
  fi

  if [ "${DJANGO_REENCRYPT_MFA_AUTHENTICATORS:-1}" = "1" ]; then
    log "Encrypting legacy MFA secrets ..."
    python manage.py reencrypt_mfa_authenticators
  fi

  log "Running auth/session maintenance bootstrap ..."
  python manage.py run_auth_maintenance --once --db-wait-seconds 0

  log "Syncing feature flag registry ..."
  python manage.py sync_feature_registry

  if [ "${DJANGO_COLLECTSTATIC:-1}" = "1" ]; then
    log "Collecting static ..."
    python manage.py collectstatic --noinput
  fi

  if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_EMAIL:-}" ] ; then
    log "Ensuring superuser ${DJANGO_SUPERUSER_USERNAME} exists ..."
    python manage.py ensure_superuser \
      --username "${DJANGO_SUPERUSER_USERNAME}" \
      --email "${DJANGO_SUPERUSER_EMAIL}" \
      --password "${DJANGO_SUPERUSER_PASSWORD:-}"
  fi
}

wait_for_db
django_bootstrap

log "Starting app: $*"
exec "$@"
