# Frontend Conventions

## Component System

Gravity UI - основной component system для нового UI. Bootstrap и
react-bootstrap остаются только как legacy exceptions.

Текущие Bootstrap exceptions:

- Global Bootstrap CSS в `src/main.jsx`: оставить, пока не уйдут Bootstrap
  classes.
- `Header` offcanvas: заменить на Gravity UI или accessible custom drawer.
- `ImageCarousel`: оставить, пока не выбран replacement carousel.
- `NotFound`: заменить на Gravity UI layout и button.

## File Shape

Предпочитаем небольшие файлы с одной ответственностью. Component files обычно
должны оставаться в пределах 250-300 строк. Form bodies, validation helpers,
rows, dialogs и skeletons лучше выносить, когда они становятся independently
testable.

## Services

Не добавляйте новые монолитные `services/api` файлы. Используйте существующее
разделение:

- `services/http/client.js` для HTTP client config.
- `services/auth/tokenStore.js` для token/session storage.
- `services/auth/sessionClient.js` для retry/refresh/logout behavior.
- `services/api/*Api.js` для domain API calls.
- `services/errors.js` для shared error parsing.
- `services/urlSafety.js` для redirect/URL safety helpers.

`services/api.js` существует только как compatibility barrel.

## Styling

Reusable surfaces должны использовать shared components или CSS modules/classes
вместо повторяющихся inline style objects. Не добавляйте Bootstrap classes в
новый код, если файл не указан как legacy exception.

## Tests

Используйте Vitest для unit tests и React Testing Library для components. Auth,
session retry, password/profile validation, account sessions и protected routes
должны получать tests до более глубоких refactors.
