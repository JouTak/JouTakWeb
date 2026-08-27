# Contributing

## Developer workflow

Основной локальный сценарий — zero-config development stack:

```bash
docker compose up --build
```

Команда на чистом checkout сама поднимает PostgreSQL, backend, frontend,
maintenance worker и локальный proxy. Не копируйте `.env.example`
в `.env`: это production-oriented template, а `compose.yaml` уже содержит
безопасные local defaults.

Оба приложения работают в development-режиме: Django runserver
перезапускается при изменении Python, Vite обновляет frontend через
HMR. Для проверки frontend→backend integration открывайте
`http://localhost`: frontend использует same-origin API/BFF paths, а Vite
проксирует их в backend без отдельного browser-visible API URL. API также
доступен напрямую на `http://api.localhost`, admin — на
`http://admin.localhost/admin/`.

Компоненты можно запускать без Docker:

- frontend: Node.js `24.18.0`, npm `11.16.0`, затем
  `cd frontend && npm ci && npm run dev`;
- backend: Python 3.12, `uv sync --locked --python 3.12 --group dev --group test`,
  migrations, `sync_feature_registry` и `runserver` с
  `backend.settings.dev`.

Полные команды и адреса описаны в [README](README.md#локальная-разработка).
Обычная остановка — `docker compose down`. Команда
`docker compose down -v` дополнительно удаляет локальную базу и media;
используйте её только для намеренного reset.

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
docker compose config >/dev/null
docker compose up -d --build
uv run python scripts/smoke_stack.py
docker compose down
docker compose -f docker-compose.yml config >/dev/null
docker compose -f docker-compose.images.yml config >/dev/null
```

## Lockfiles

Коммитьте `frontend/package-lock.json`, когда меняются frontend dependencies.
Коммитьте `pyproject.toml` и `uv.lock`, когда меняются backend dependencies.
Временные requirements для image build и audit генерируются из `uv.lock` и не
хранятся в репозитории.
