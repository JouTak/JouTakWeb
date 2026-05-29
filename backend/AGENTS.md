# backend/AGENTS.md

Правила для агентов, работающих только в `backend/`.

## Базовые конвенции

- Django Ninja routers должны быть тонкими.
- Порядок работы router:
  1. authenticate / authorize.
  2. принять typed request schemas.
  3. вызвать service methods.
  4. вернуть typed response schemas.
- Business logic должна жить рядом с соответствующим app:
  - `backend/accounts/services/` для account/auth flows.
  - `backend/bff/services.py` для BFF helpers и orchestration.
  - `backend/featureflags/services.py` для feature-flag logic.
- Request/response schemas и transport-слой должны жить рядом с app, который ими владеет.
- Публичные error responses должны использовать structured error helpers, а не JSON strings внутри `HttpError`.

## Контракты и валидация

- Стабильные ограничения ставь на schema boundary: max lengths, min lengths, patterns, bounded list sizes и ограниченные enum-like values.
- Если endpoint может вернуть schema-boundary validation error, добавляй `422` в OpenAPI response map.
- Предпочитай явные response schemas вместо `dict[str, object]` и `list[dict]`.
- Compatibility endpoints сохраняй только пока от них зависит существующий frontend code.

## Структура кода

- `backend/accounts/api/` - Ninja routers и exception handling для account/auth APIs.
- `backend/accounts/services/` - business logic для account/auth flows.
- `backend/accounts/transport/schemas.py` - request/response contracts для account/auth APIs.
- `backend/accounts/tests/` - API и service regression tests для account/auth flows.
- `backend/bff/` - BFF helpers, services и tests.
- `backend/featureflags/` - feature flag services, management commands, migrations и tests.
- `backend/observability/` - observability helpers и tests.
- `backend/core/` - shared models and infrastructure.
- `backend/backend/` - project settings, top-level backend tests и Django bootstrapping.

## Практика изменения кода

- Держи routers thin: authenticate, validate schemas, call services, return typed schemas.
- Если меняешь API contracts, обновляй frontend contract check и связанные тесты.
- Если меняешь auth, sessions, profile, password, OAuth или account deletion, добавляй или обновляй tests в `backend/accounts/tests/`.
- Если меняешь BFF, feature flags или observability code, обновляй тесты и местные app-level проверки в соответствующем пакете.
- Не редактируй generated requirements вручную.

## Проверки

Запускай релевантные backend-проверки:

```bash
uv run ruff check .
uv run bandit -r backend/accounts backend/bff backend/core backend/featureflags backend/observability backend/backend -x "*/tests/*,*/migrations/*" --skip B104,B105
PYTHONPATH=backend DJANGO_SETTINGS_MODULE=backend.settings.dev uv run python scripts/check_frontend_openapi_contracts.py
uv run pytest backend -q
```

Обычно достаточно выбрать подзадачу:

- Python-only refactor - `ruff check` + релевантные tests.
- Contract change - `ruff check` + `check_frontend_openapi_contracts.py` + tests.
- Security-sensitive change - добавляй `bandit`.
- Любая правка поведения - добавляй `pytest`.

## Зависимости и окружение

- Backend dependencies меняй через `uv`.
- Коммить `uv.lock` и regenerated files в `backend/requirements/`, когда меняются backend dependencies.
- `.env`, `.env.development`, `.env.production` и secret variants должны оставаться локальными.
- `stack.yml` ожидает production secrets через Docker secrets и локальный `.env.production`; этот файл не коммитится.
