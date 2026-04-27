# Architecture

## Backend

Backend - это Django project в `backend/backend`, application code в
`backend/accounts` и shared models в `backend/core`.

- `accounts/api/` содержит Ninja routers и exception handling.
- `accounts/transport/schemas.py` описывает request и response contracts.
- `accounts/services/` владеет business logic для auth, sessions, OAuth,
  email, profile и account status.
- `accounts/tests/` содержит API и service regression tests.
- `core/models.py` содержит shared user profile и session metadata models.

API routers должны оставаться тонкими: authenticate, validate schemas, call
services и return typed schemas.

## Frontend

Frontend - это Vite React app в `frontend`.

- `src/pages/` содержит route-level pages.
- `src/components/` содержит shared и feature components.
- `src/components/account/` содержит account security/profile surfaces.
- `src/services/http/client.js` владеет axios и backend URL config.
- `src/services/auth/tokenStore.js` владеет browser auth storage.
- `src/services/auth/sessionClient.js` владеет allauth/session retry behavior.
- `src/services/api/` содержит domain API modules.
- `src/services/api.js` - compatibility barrel для существующих imports.

## Auth And Account Flow

Frontend логинится через allauth headless app endpoints, хранит session token в
`sessionStorage`, обменивает его на access token и отправляет `X-Session-Token`
плюс `Authorization`, когда он доступен. Refresh использует session-bound
refresh cookie и требует текущий session token.

Account pages вызывают backend Ninja endpoints для profile, status, sessions,
OAuth links, password changes и account deletion. Email confirmation и password
reset остаются на allauth headless endpoints.

## Docker Services

- `db`: PostgreSQL.
- `backend`: Django/Gunicorn API container.
- `backend-maintenance`: scheduled/manual auth maintenance command.
- `frontend`: nginx-served Vite build.
- `traefik`: production Swarm ingress в `stack.yml`.

Локальная разработка использует `docker-compose.local.yml`. Image-based
deployment использует `docker-compose.images.yml` или `stack.yml`.

## CI Jobs

CI разделяет frontend checks, backend checks, Docker validation/builds, commit
rules и secret scanning. Названия jobs должны быть конкретными, чтобы по
падению было быстро понятно, кто владелец проблемы.
