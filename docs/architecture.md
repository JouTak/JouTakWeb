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
- `backend`: Django API; default `compose.yaml` запускает development
  `runserver`, production manifests — Gunicorn.
- `backend-maintenance`: scheduled/manual auth maintenance command.
- `frontend`: Vite dev server в `compose.yaml`, nginx-served build в
  production manifests.
- `proxy`: локальный nginx для frontend, API и admin host routing.
- `traefik`: production Swarm ingress в `docker-compose.stack.yml`.

Локальная разработка использует `compose.yaml` и запускается командой
`docker compose up --build`. Image-based deployment использует
`docker-compose.images.yml` или `docker-compose.stack.yml`.

## CI Jobs

CI разделяет frontend checks, backend checks, Docker validation/builds, commit
rules и secret scanning. Названия jobs должны быть конкретными, чтобы по
падению было быстро понятно, кто владелец проблемы.

## Community Profile Hub

`profiles` owns opt-in public representation and visibility serialization;
`core.UserProfile` remains the private personalization source. `communities`
owns trusted server communities/memberships. `cities` owns structured pages,
scoped governance, moderation, transactional audit and content revisions.
The existing BFF bootstrap delivers rollout flags only; memberships are fetched
on account/profile pages. New mutations retain session-token authorization.

See [Community Hub architecture](cities/architecture.md),
[domain model](cities/domain-model.md), [RBAC](cities/rbac.md),
[BlueMap ADR](cities/adr.md) and [local review / rollout](cities/rollout.md).

`profiles` also owns opt-in player discovery, directed subscriptions and typed
Discord/Telegram/VK contacts. Search and connection lists apply visibility before
pagination; subscription does not grant access. The `/players` directory uses the
existing profile rollout flag. See [player connections](cities/player-connections.md).

Profile editing uses partial typed writes and independent optimistic versions for
presentation and contacts, with User-row locking shared by the legacy account
writer. Guest preview calls the same public projections with an anonymous viewer;
own following management exposes no identity for inaccessible targets.
See [editing and preview ADR](profiles/adr-001-safe-editing-and-preview.md) and
[local verification and QA](profiles/implementation-report-2026-09-21.md).

## Player groups

`playergroups` owns voluntary clubs, teams and guilds. Its participation never
expands the trusted server audience used by profiles or city permissions.
Invitations, applications and leadership offers are separate consent processes.
The common `/communities` catalog distinguishes official server communities
from player-created groups; moderation uses a dedicated Django permission.

See [domain decisions](communities/adr-001-community-groups.md),
[API and state transitions](communities/implementation.md), and
[local review / rollout](communities/rollout.md).
