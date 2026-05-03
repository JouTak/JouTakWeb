# API Conventions

## Backend Shape

Django Ninja routers задают публичную границу API. Держим routers тонкими:

1. Authenticate и authorize.
2. Принимать typed request schemas.
3. Вызывать service methods.
4. Возвращать typed response schemas.

Business logic должна жить в `accounts/services/`. Request/response schemas
должны жить в `accounts/transport/schemas.py`.

## Validation

Стабильные ограничения ставим на schema boundary: max lengths, min lengths,
patterns, bounded list sizes и ограниченные enum-like values. Services все еще
могут нормализовать данные и проверять cross-field rules.

Если endpoint может вернуть schema-boundary validation error, добавляйте `422`
в OpenAPI response map. Это важно для frontend contracts: клиент должен видеть,
что ошибка пришла до business logic, а не как обычный `400`.

## Errors

Публичные error responses держим в следующем формате:

```json
{
  "detail": "validation_error",
  "code": 400,
  "error_code": "OPTIONAL_BUSINESS_CODE",
  "blocking_reasons": ["OPTIONAL_REASON"],
  "errors": {
    "field": [{ "message": "Human readable", "code": "invalid" }]
  },
  "fields": {
    "field": "Human readable"
  }
}
```

Не стоит создавать structured errors через JSON strings внутри `HttpError`.
Используйте structured error helpers из `accounts/api/errors.py`.

## Responses

Предпочитайте явные response schemas вместо `dict[str, object]` и `list[dict]`.
Если compatibility fields нужно оставить, держите их описанными в schema до
миграции frontend.

## Deprecation

Compatibility endpoints оставляем, пока от них зависит существующий frontend
код, но новый frontend код должен использовать canonical endpoints. Например,
используйте `/account/sessions/bulk` вместо `/account/sessions/_bulk`.

## OpenAPI

OpenAPI document доступен из Ninja API по `/api/openapi.json`. Используйте его
на review, чтобы сравнивать изменения frontend/API contracts.

Для автоматической проверки frontend calls против Ninja OpenAPI запускайте:

```bash
PYTHONPATH=backend DJANGO_SETTINGS_MODULE=backend.settings.dev uv run python scripts/check_frontend_openapi_contracts.py
```

Скрипт проверяет наличие Ninja endpoints, expected request body schemas,
динамические path/query parameters и обязательные `422` responses для
schema-boundary cases.

Allauth headless endpoints под `/api/auth/flow/app/v1/*` не генерируются этим
Ninja OpenAPI document. Для них держим frontend wrapper'ы отдельно и покрываем
tests вокруг login, signup, email confirmation и password reset flows.
