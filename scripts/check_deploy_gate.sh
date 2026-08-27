#!/usr/bin/env bash
set -euo pipefail

run_smoke="${RUN_SMOKE:-0}"
if [[ "${1:-}" == "--smoke" ]]; then
  run_smoke="1"
fi

uv run ruff check .
uv run bandit -r backend/accounts backend/core backend/backend backend/featureflags backend/observability -x "*/tests/*,*/migrations/*" --skip B104,B105
PYTHONPATH=backend DJANGO_SETTINGS_MODULE=backend.settings.dev uv run python scripts/check_frontend_openapi_contracts.py
uv run python backend/manage.py check
DJANGO_SETTINGS_MODULE=backend.settings.dev PYTHONPATH=backend uv run pytest backend -q
npm --prefix frontend run check

docker compose -f compose.yaml config >/dev/null

POSTGRES_DB=gate_db \
POSTGRES_USER=gate_user \
POSTGRES_PASSWORD=gate_password \
DJANGO_SECRET_KEY=gate-secret-key-change-me \
FRONTEND_BASE_URL=https://joutak.ru \
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,joutak.localhost,api.localhost,admin.localhost,joutak.ru,api.joutak.ru,admin.joutak.ru \
DJANGO_ADMIN_HOSTS=admin.localhost,admin.joutak.ru \
DJANGO_API_HOSTS=localhost,joutak.localhost,api.localhost,joutak.ru,api.joutak.ru \
DJANGO_CSRF_TRUSTED_ORIGINS=https://joutak.ru \
CORS_ALLOWED_ORIGINS=http://localhost,http://127.0.0.1,https://joutak.ru \
PUBLIC_API_URL=http://api.localhost \
WEBAUTHN_RP_ID=joutak.ru \
WEBAUTHN_RP_NAME=JouTak \
WEBAUTHN_ACCOUNT_ORIGINS=https://joutak.ru \
WEBAUTHN_ADMIN_ORIGINS=https://admin.joutak.ru \
WEBAUTHN_ALLOWED_ORIGINS=https://joutak.ru,https://admin.joutak.ru \
docker compose -f docker-compose.yml config >/dev/null

POSTGRES_DB=gate_db \
POSTGRES_USER=gate_user \
POSTGRES_PASSWORD=gate_password \
DJANGO_SECRET_KEY=gate-secret-key-change-me \
FRONTEND_BASE_URL=https://joutak.ru \
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,joutak.localhost,api.localhost,admin.localhost,joutak.ru,api.joutak.ru,admin.joutak.ru \
DJANGO_ADMIN_HOSTS=admin.localhost,admin.joutak.ru \
DJANGO_API_HOSTS=localhost,joutak.localhost,api.localhost,joutak.ru,api.joutak.ru \
DJANGO_CSRF_TRUSTED_ORIGINS=https://joutak.ru \
CORS_ALLOWED_ORIGINS=http://localhost,http://127.0.0.1,https://joutak.ru \
PUBLIC_API_URL=http://api.localhost \
WEBAUTHN_RP_ID=joutak.ru \
WEBAUTHN_RP_NAME=JouTak \
WEBAUTHN_ACCOUNT_ORIGINS=https://joutak.ru \
WEBAUTHN_ADMIN_ORIGINS=https://admin.joutak.ru \
WEBAUTHN_ALLOWED_ORIGINS=https://joutak.ru,https://admin.joutak.ru \
docker compose -f docker-compose.images.yml config >/dev/null

trap 'rm -f .env.production' EXIT
cp .env.example .env.production

POSTGRES_DB=gate_db \
POSTGRES_USER=gate_user \
POSTGRES_PASSWORD=gate_password \
DJANGO_SECRET_KEY=gate-secret-key-change-me \
FRONTEND_BASE_URL=https://joutak.ru \
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,joutak.localhost,api.localhost,admin.localhost,joutak.ru,api.joutak.ru,admin.joutak.ru \
DJANGO_ADMIN_HOSTS=admin.localhost,admin.joutak.ru \
DJANGO_API_HOSTS=localhost,joutak.localhost,api.localhost,joutak.ru,api.joutak.ru \
DJANGO_CSRF_TRUSTED_ORIGINS=https://joutak.ru \
CORS_ALLOWED_ORIGINS=http://localhost,http://127.0.0.1,https://joutak.ru \
PUBLIC_API_URL=https://joutak.ru/api \
WEBAUTHN_RP_ID=joutak.ru \
WEBAUTHN_RP_NAME=JouTak \
WEBAUTHN_ACCOUNT_ORIGINS=https://joutak.ru \
WEBAUTHN_ADMIN_ORIGINS=https://admin.joutak.ru \
WEBAUTHN_ALLOWED_ORIGINS=https://joutak.ru,https://admin.joutak.ru \
TRAEFIK_ACME_EMAIL=ops@example.com \
docker compose -f stack.yml config >/dev/null

if [[ "${run_smoke}" == "1" ]]; then
  docker compose down -v || true
  docker compose up -d --build
  trap 'docker compose down -v; rm -f .env.production' EXIT
  uv run python scripts/smoke_stack.py
fi
