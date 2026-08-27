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
frontend/                 Vite React application
frontend/src/services/    Frontend HTTP, auth/session and API clients
docs/                     Contributor, architecture and security docs
.github/workflows/        CI and release workflows
compose.yaml              Default local Compose entry point
docker-compose*.yml       Image-based Compose entry points and overrides
docker-compose.stack.yml  Docker Swarm production stack template
```

## Локальная разработка

### Full stack в Docker

Для основного dev-flow нужны только Git, Docker и Docker Compose.
На чистом checkout не нужно создавать `.env` или знать параметры
backend:

```bash
docker compose up --build
```

Первый запуск соберёт образы, поднимет PostgreSQL, применит миграции,
синхронизирует feature registry и запустит весь стек. После запуска доступны:

- frontend через proxy: `http://localhost`;
- Vite напрямую: `http://localhost:5173`;
- API/BFF: `http://api.localhost`;
- Django admin: `http://admin.localhost/admin/`;
- backend health: `http://api.localhost/health/`.

`compose.yaml` — development-стек: Django работает с `DEBUG=True` и
autoreload, frontend — через Vite HMR. Исходники подключены в контейнеры,
поэтому после изменения Python, JavaScript, JSX и CSS пересборка образа
не нужна. Пересобирайте образ только после изменения dependencies или
Dockerfile.

Полезные команды:

```bash
# Поднять весь стек в background
docker compose up -d --build

# Статус и логи
docker compose ps
docker compose logs -f backend frontend

# Django shell в dev-container
docker compose exec backend python manage.py shell

# Только backend с PostgreSQL (db поднимется автоматически)
docker compose up --build backend

# Frontend/HMR вместе с его backend и PostgreSQL dependencies
docker compose up --build frontend

# Остановить стек, сохранив базу
docker compose down
```

`docker compose down -v` удалит локальную PostgreSQL и загруженные
media. Используйте эту команду только для намеренного полного reset.

Рекомендуемые сценарии по ролям:

- frontend-разработчик может поднять готовые backend и PostgreSQL командой
  `docker compose up -d --build backend`, а Vite запустить нативно через
  `npm run dev`; параметры backend и env-файл для этого не нужны;
- backend-разработчик может выполнить `docker compose up --build frontend`:
  Compose автоматически поднимет PostgreSQL и backend dependency, после чего
  интеграцию можно проверять на `http://localhost:5173`;
- для сквозной проверки с локальным proxy и maintenance worker используйте
  полный `docker compose up --build`.

### Frontend без Docker

Нужны Node.js `24.18.0` и npm `11.16.0`. Версия Node зафиксирована в
`.node-version`, а npm — в `frontend/package.json`.

```bash
npm --prefix frontend ci
npm --prefix frontend run dev
```

Frontend откроется на `http://localhost:5173` и по умолчанию будет
делать same-origin запросы. Vite сам проксирует `/api`, `/bff`, `/accounts`,
`/media` и `/health` на backend `http://127.0.0.1:8000`, поэтому задавать
frontend API URL не нужно. Без backend интерфейс откроется, но auth/BFF-запросы
будут ожидаемо завершаться ошибкой.

Проверки frontend:

```bash
npm --prefix frontend run check
```

### Backend без Docker

Нужны Python 3.12 и [uv](https://docs.astral.sh/uv/). Без `DATABASE_URL`
development settings используют SQLite, поэтому PostgreSQL для такого
запуска не нужен.

```bash
uv sync --locked --python 3.12 --group dev --group test
uv run python backend/manage.py migrate --settings backend.settings.dev
uv run python backend/manage.py sync_feature_registry --settings backend.settings.dev
uv run python backend/manage.py runserver 127.0.0.1:8000 --settings backend.settings.dev
```

Адреса для прямого запуска: API — `http://api.localhost:8000`, Django admin —
`http://admin.localhost:8000/admin/`, health — `http://127.0.0.1:8000/health/`.

Проверки backend:

```bash
uv run ruff check .
PYTHONPATH=backend DJANGO_SETTINGS_MODULE=backend.settings.dev uv run python scripts/check_frontend_openapi_contracts.py
uv run pytest backend -q
```

Если нужен весь поток передачи данных между frontend и backend, не собирайте
части стека вручную: используйте `docker compose up --build`.

## Environment Files

- Для `compose.yaml` env-файл не нужен. Все defaults предназначены только
  для локальной development-среды. Необязательные overrides имеют префикс
  `DEV_`, например `DEV_HTTP_PORT`, `DEV_BACKEND_PORT`,
  `DEV_FRONTEND_PORT` и `DEV_CHOKIDAR_USEPOLLING`.
- При смене опубликованных портов согласуйте `DEV_FRONTEND_BASE_URL` и
  `DEV_DJANGO_CSRF_TRUSTED_ORIGINS` с адресом, через который открываете
  frontend.
- `.env.example` — очищенный production-oriented template. Не копируйте его
  в `.env` для обычного локального запуска. Production-переменные намеренно
  не переопределяют безопасные defaults из `compose.yaml`.
- `.env`, `.env.development`, `.env.production` и secret variants остаются
  локальными.
- `docker-compose.stack.yml` ожидает production secrets через Docker secrets и
  локальный
  `.env.production`; этот файл нельзя коммитить.
- Optional `*_FILE` variables имеют приоритет там, где поддерживаются.

## Dependencies

Frontend dependencies меняются через npm и коммитятся вместе с
`frontend/package-lock.json`:

```bash
npm --prefix frontend install <package>
npm --prefix frontend uninstall <package>
```

Backend dependencies меняются через uv. Коммитьте `pyproject.toml` и
`uv.lock`; временные requirements для image build и audit генерируются из
lockfile и не хранятся в репозитории:

```bash
uv add <package>
uv add --group dev <package>
uv add --group test <package>
uv lock --check
uv export --frozen --no-dev --no-hashes -o /tmp/joutak-requirements.txt
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
