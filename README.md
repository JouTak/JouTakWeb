# JouTakWeb

[![CI](https://github.com/JouTak/JouTakWeb/actions/workflows/CI.yml/badge.svg)](https://github.com/JouTak/JouTakWeb/actions/workflows/CI.yml)
![GitHub top language](https://img.shields.io/github/languages/top/JouTak/JouTakWeb)

JouTakWeb - web-приложение для серверов комьюнити JouTak x ITMOcraft.

## Стек

- Frontend: React 18, Vite, Gravity UI, legacy Bootstrap components, npm.
- Backend: Python 3.12+, Django 5.2, Django Ninja, django-allauth, uv.
- Database: PostgreSQL в Docker, SQLite для отдельных test runs.
- Tooling: Ruff, Bandit, pip-audit, ESLint, Prettier, Stylelint, Vitest.

## Структура Репозитория

```text
backend/                  Django project, apps, tests, Dockerfile
backend/accounts/         Auth, account, OAuth and session APIs
backend/core/             Shared backend models and infrastructure
backend/requirements/     Generated uv exports for container installs
frontend/                 Vite React application
frontend/src/services/    Frontend HTTP, auth/session and API clients
docs/                     Contributor, architecture and security docs
.github/workflows/        CI and release workflows
compose.yaml              Default local Compose entry point
docker-compose*.yml       Image-based Compose entry points and overrides
stack.yml                 Docker Swarm production stack template
```

## Для начала работы вам потребуется

- Git.
- Node.js `>=20.19`; для локальной разработки предпочтительно Node 22.
- npm, поставляется вместе с Node.
- Python 3.12.
- [uv](https://docs.astral.sh/uv/) для Python dependency management.
- Docker и Docker Compose для локального full stack.

### Запуск Frontend

```bash
cd frontend
npm ci
npm run dev
```

Dev server выведет локальный URL, обычно `http://localhost:5173`.

Backend не является обязательной зависимостью для `npm run dev`: интерфейс
должен открываться и без поднятого API. При этом auth/BFF-запросы будут
ошибаться, что ожидаемо для standalone frontend development.

Проверки frontend:

```bash
npm --prefix frontend run lint
npm --prefix frontend run format
npm --prefix frontend run lint:styles
npm --prefix frontend run test:run
npm --prefix frontend run build
npm --prefix frontend run check
```

### Запуск Backend

```bash
uv sync --python 3.12 --group dev --group test
uv run python backend/manage.py migrate --settings backend.settings.dev
uv run python backend/manage.py runserver 8000 --settings backend.settings.dev
```

Проверки backend:

```bash
uv run ruff check .
uv run bandit -r backend/accounts backend/core backend/backend -x "*/tests/*,*/migrations/*" --skip B104,B105
PYTHONPATH=backend DJANGO_SETTINGS_MODULE=backend.settings.dev uv run python scripts/check_frontend_openapi_contracts.py
uv export --frozen --no-dev --no-hashes -q -o /tmp/joutak-requirements.txt
uv run pip-audit --no-deps -r /tmp/joutak-requirements.txt
uv run pytest backend -q
```

### Локальный Docker Stack

Создайте локальный env-файл из очищенного примера и замените placeholder values:

`compose.yaml` теперь является дефолтным локальным Compose-файлом, поэтому
достаточно короткой команды:

```bash
cp .env.example .env
docker compose up --build
```

По умолчанию локальный стек остаётся HTTP-only, чтобы `docker compose up
--build` не упирался в TLS-redirect loop. Для `Passkeys` локально включён
`MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN`, а если нужен именно HTTPS-сценарий
для ручной проверки, поднимайте production-style stack или свой TLS
override.

Полезные команды для сверки конфигов:

```bash
docker compose config >/dev/null
docker compose -f docker-compose.yml config >/dev/null
docker compose -f docker-compose.images.yml config >/dev/null
```

## Environment Files

- `.env.example` содержит только очищенные placeholders.
- `.env`, `.env.development`, `.env.production` и secret variants остаются
  локальными.
- `stack.yml` ожидает production secrets через Docker secrets и локальный
  `.env.production`; этот файл нельзя коммитить.
- Optional `*_FILE` variables имеют приоритет там, где поддерживаются.

## Dependencies

Frontend dependencies меняются через npm и коммитятся вместе с
`frontend/package-lock.json`:

```bash
npm --prefix frontend install <package>
npm --prefix frontend uninstall <package>
```

Backend dependencies меняются через uv. Generated requirements руками не
редактируем:

```bash
uv add <package>
uv add --group dev <package>
uv add --group test <package>
uv export --frozen --no-dev --no-hashes -o backend/requirements/prod.txt
uv export --frozen --group dev --group test --no-hashes -o backend/requirements/dev.txt
uv export --frozen --no-default-groups --group test --no-hashes -o backend/requirements/test.txt
```

## CI

CI запускает frontend lint/format/style/test/build/audit, backend Ruff/Bandit/
pip-audit/tests, Docker config/build checks, commit rules для PR и secret
scanning.

## Документация Для Участников

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [Архитектура](docs/architecture.md)
- [Безопасность](docs/security.md)
- [Frontend Conventions](docs/frontend-conventions.md)
- [API Conventions](docs/api-conventions.md)
