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

POSTGRES_DB=gate_db \
POSTGRES_USER=gate_user \
POSTGRES_PASSWORD=gate_password \
DJANGO_SECRET_KEY=gate-secret-key-change-me \
FRONTEND_BASE_URL=https://joutak.ru \
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,api.localhost,admin.localhost,api.joutak.ru,admin.joutak.ru \
DJANGO_ADMIN_HOSTS=admin.localhost,admin.joutak.ru \
DJANGO_API_HOSTS=api.localhost,api.joutak.ru \
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost,http://127.0.0.1,http://api.localhost,http://admin.localhost,https://joutak.ru,https://api.joutak.ru,https://admin.joutak.ru \
CORS_ALLOWED_ORIGINS=http://localhost,http://127.0.0.1,https://joutak.ru \
PUBLIC_API_URL=http://api.localhost \
docker compose -f docker-compose.yml config >/dev/null

POSTGRES_DB=gate_db \
POSTGRES_USER=gate_user \
POSTGRES_PASSWORD=gate_password \
DJANGO_SECRET_KEY=gate-secret-key-change-me \
FRONTEND_BASE_URL=https://joutak.ru \
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,api.localhost,admin.localhost,api.joutak.ru,admin.joutak.ru \
DJANGO_ADMIN_HOSTS=admin.localhost,admin.joutak.ru \
DJANGO_API_HOSTS=api.localhost,api.joutak.ru \
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost,http://127.0.0.1,http://api.localhost,http://admin.localhost,https://joutak.ru,https://api.joutak.ru,https://admin.joutak.ru \
CORS_ALLOWED_ORIGINS=http://localhost,http://127.0.0.1,https://joutak.ru \
PUBLIC_API_URL=http://api.localhost \
docker compose -f docker-compose.local.yml config >/dev/null

trap 'rm -f .env.production' EXIT
cp .env.example .env.production

POSTGRES_DB=gate_db \
POSTGRES_USER=gate_user \
POSTGRES_PASSWORD=gate_password \
DJANGO_SECRET_KEY=gate-secret-key-change-me \
FRONTEND_BASE_URL=https://joutak.ru \
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,api.localhost,admin.localhost,api.joutak.ru,admin.joutak.ru \
DJANGO_ADMIN_HOSTS=admin.localhost,admin.joutak.ru \
DJANGO_API_HOSTS=api.localhost,api.joutak.ru \
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost,http://127.0.0.1,http://api.localhost,http://admin.localhost,https://joutak.ru,https://api.joutak.ru,https://admin.joutak.ru \
CORS_ALLOWED_ORIGINS=http://localhost,http://127.0.0.1,https://joutak.ru \
PUBLIC_API_URL=https://api.joutak.ru \
docker compose -f stack.yml config >/dev/null

if [[ "${run_smoke}" == "1" ]]; then
  docker compose -f docker-compose.local.yml down -v || true
  docker compose -f docker-compose.local.yml up -d --build
  trap 'docker compose -f docker-compose.local.yml down -v; rm -f .env.production' EXIT
  uv run python scripts/smoke_stack.py
fi
