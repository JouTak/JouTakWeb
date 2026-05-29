# backend/AGENTS.md

Правила для агентов, работающих только в `backend/`.

## Базовые конвенции

- Django Ninja routers должны быть тонкими.
- Порядок работы router:
  1. authenticate / authorize.
  2. принять typed request schemas.
  3. вызвать service methods.
  4. вернуть typed response schemas.
- Business logic должна жить в `backend/accounts/services/`.
- Request/response schemas должны жить в `backend/accounts/transport/schemas.py`.
- Публичные error responses должны использовать structured error helpers, а не JSON strings внутри `HttpError`.

## Контракты и валидация

- Стабильные ограничения ставь на schema boundary: max lengths, min lengths, patterns, bounded list sizes и ограниченные enum-like values.
- Если endpoint может вернуть schema-boundary validation error, добавляй `422` в OpenAPI response map.
- Предпочитай явные response schemas вместо `dict[str, object]` и `list[dict]`.
- Compatibility endpoints сохраняй только пока от них зависит существующий frontend code.

## Структура кода

- `backend/accounts/api/` - Ninja routers и exception handling.
- `backend/accounts/services/` - business logic.
- `backend/accounts/transport/schemas.py` - request/response contracts.
- `backend/accounts/tests/` - API и service regression tests.
- `backend/core/` - shared models and infrastructure.

## Практика изменения кода

- Держи routers thin: authenticate, validate schemas, call services, return typed schemas.
- Если меняешь API contracts, обновляй frontend contract check и связанные тесты.
- Если меняешь auth, sessions, profile, password, OAuth или account deletion, добавляй или обновляй тесты.
- Не редактируй generated requirements вручную.

## Проверки

Запускай релевантные backend-проверки:

```bash
uv run ruff check .
uv run bandit -r backend/accounts backend/core backend/backend -x "*/tests/*,*/migrations/*" --skip B104,B105
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
