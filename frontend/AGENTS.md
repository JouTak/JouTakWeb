# frontend/AGENTS.md

Правила для агентов, работающих только в `frontend/`.

## Базовые конвенции

- Новый UI строится на Gravity UI по умолчанию.
- Bootstrap и `react-bootstrap` считаются legacy exceptions и не должны расширяться без причины.
- Не добавляй новые Bootstrap classes в свежий код, если файл не относится к явно legacy-участку.
- Ориентир по размеру component file - примерно 250-300 строк; если файл растёт, выноси формы, helpers, dialogs и skeletons.
- Предпочитай небольшие файлы с одной ответственностью.

## Структура кода

- `src/pages/` - route-level pages.
- `src/components/` - shared и feature components.
- `src/components/account/` - account, security и profile surfaces.
- `src/services/http/client.js` - HTTP client и backend URL config.
- `src/services/auth/tokenStore.js` - browser auth storage.
- `src/services/auth/sessionClient.js` - session retry, refresh и logout behavior.
- `src/services/api/` - domain API modules.
- `src/services/api.js` - compatibility barrel для старых imports.

## Практика изменения кода

- Не создавай новые монолитные `services/api` файлы.
- Для API-клиентов используй существующее разбиение по `services/api/*Api.js`.
- Для shared helpers используй `services/errors.js` и `services/urlSafety.js`, а не дублируй логику.
- Если затрагиваешь auth, session retry, password/profile validation, sessions, protected routes или API contracts, добавляй или обновляй тесты до глубокого рефакторинга.
- Если меняешь legacy-участок, не расширяй legacy-стиль за пределы уже существующего участка.

## Проверки

Запускай релевантные frontend-проверки:

```bash
npm --prefix frontend run lint
npm --prefix frontend run format
npm --prefix frontend run lint:styles
npm --prefix frontend run test:run
npm --prefix frontend run build
npm --prefix frontend run check
```

Обычно достаточно выбрать подзадачу:

- UI/JS logic - `lint` + `test:run`.
- Styling changes - `lint:styles`.
- Dependency or production-sensitive change - `check`.
- Если меняется сборка или роутинг - добавляй `build`.

## Локальные исключения

- Global Bootstrap CSS в `src/main.jsx` оставляй, пока в проекте ещё есть Bootstrap classes.
- `Header` offcanvas можно менять на Gravity UI или accessible custom drawer.
- `ImageCarousel` можно оставить, пока не выбран replacement.
- `NotFound` желательно переводить на Gravity UI layout и button.
