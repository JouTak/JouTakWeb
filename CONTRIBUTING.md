# Contributing

## Branches

Используйте короткие scoped branches. Рекомендуем для dev наработок использовать префикс - `dev/`, например:

```text
dev/frontend-api-split
dev/backend-contracts
dev/docs-baseline
```

## Commits

При оформлении сообщений обязательно следуйте оформлению commit messages по [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0-beta.3/):

```text
type(scope): description
```

Пример разрешенных типов: `feat`, `fix`, `chore`, `refactor`, `docs`, `test`, `ci`,
`build`, `perf`, `style`, `revert`.

Примеры:

```text
fix(api): validate session revoke payload
refactor(frontend): split auth session client
docs(security): document secret handling
```

Merge commits, созданные GitHub, разрешены. Ручные commits должны следовать
формату выше. `git commit --no-verify` используйте только для emergency work и
объясняйте причину в PR.

## Pull Requests

Составляйте PR с хорошей читаемостью. Лучше один behavior change или один mechanical refactor
на PR. Не прячьте behavior changes внутри cleanup-only refactors.

Мини чеклист корректно составленного контрибута:

- Запущены tests и linters, релевантные изменению.
- UI changes содержат screenshots или короткую visual smoke note.
- Database migrations добавлены или явно указано, что они не нужны.
- Docs актуализирован, если производили замену команд/переменных окружения/API констрактов.
- Lockfiles и requirements обновлены через команды пакетных менеджеров npm/uv.

## Команды для быстрой проверки перед PR:

Frontend:

```bash
npm --prefix frontend run check
```

Backend:

```bash
uv run ruff check .
PYTHONPATH=backend DJANGO_SETTINGS_MODULE=backend.settings.dev uv run python scripts/check_frontend_openapi_contracts.py
uv run pytest backend -q
```

Docker:

```bash
docker compose -f docker-compose.yml config >/dev/null
docker compose -f docker-compose.local.yml config >/dev/null
```

## Lockfiles

Коммитьте `frontend/package-lock.json`, когда меняются frontend dependencies.
Коммитьте `uv.lock` и regenerated files в `backend/requirements/`, когда
меняются backend dependencies. Генерируемые поля в requirement'ах руками не
редактируем.
