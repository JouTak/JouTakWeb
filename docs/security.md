# Security

## Secrets

Никогда не коммитьте реальные secrets. `.env.example` должен содержать только
placeholders. Локальные файлы вроде `.env`, `.env.development`,
`.env.production` и `*.secrets` остаются ignored.

Не вставляйте вывод `docker compose config`, CI environment dumps, Django
settings dumps или logs с env values в публичные issues и PR.

Если реальный credential был закоммичен, вставлен в лог, отправлен в review или
как-то еще раскрыт, сначала rotate его, а потом обсуждайте детали публично.

## Token And Cookie Model

Frontend хранит allauth session state в `sessionStorage`, а не в
`localStorage`. Это ограничивает persistence между browser sessions, но данные
все еще доступны JavaScript, поэтому XSS остается high impact.

Refresh привязан к активной session и использует cookie с path
`/api/auth/refresh`. Production cookies должны быть `Secure`; SameSite и domain
values должны соответствовать frontend/backend deployment mode.

## CORS And CSRF

Production `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`,
`CORS_ALLOWED_ORIGINS` и `FRONTEND_BASE_URL` должны быть явными. Localhost
origins допустимы только для local compose/dev.

## Redirects And OAuth

Frontend redirect helpers должны отклонять `javascript:`, `data:`,
protocol-relative URLs и неизвестные absolute hosts. Backend OAuth `next`
values должны оставаться internal paths.

## Uploads

Avatar uploads ограничены по size, MIME type, decoded dimensions и decoded image
format. Принятые images re-encode'ятся перед storage, чтобы убрать metadata, а
normalized output все еще должен помещаться в configured upload size limit.

## Deployment

`stack.yml` читает `.env.production` и Docker secrets. Этот env file должен
оставаться локальным или управляться deployment tooling. Traefik - intended
public ingress для Swarm; backend и frontend service ports не должны быть
напрямую exposed в production, если deployment явно этого не требует.

Не используйте mutable `latest` tags для production rollouts. Предпочитайте
immutable image tags, созданные CI.

`DB_SSL_REQUIRED=false` допустим для Docker-internal PostgreSQL networks.
External database connections должны требовать SSL.

Включайте `USE_X_FORWARDED_PROTO=true` только за trusted proxy. Настройте
trusted proxy CIDRs до того, как доверять forwarded client IP data.

## CSP And Headers

Текущий CSP allowlist намеренно достаточно permissive для существующего UI и
third-party assets. Сужение `style-src 'unsafe-inline'` зависит от удаления
inline style blocks.

### Follow-up: сужение `style-src 'unsafe-inline'`

Gravity UI и часть наших React-компонентов генерируют inline `style={...}`
атрибуты, из-за которых на фронтенде пока нельзя отказаться от
`'unsafe-inline'` в `style-src`. Это ослабляет защиту от XSS и считается
techincal debt.

План перехода (не блокер этого релиза, но must-have для следующего
security milestone'а):

1. Аудит inline-стилей: найти компоненты, где inline-стиль реально
   зависит от runtime-данных (динамические цвета, вычисленные размеры)
   и перенести остальные в CSS-классы/модули.
2. Для остаточных динамических стилей включить CSP nonce: выдавать
   per-request nonce через `django-csp` (или аналог), передавать его в
   SSR-шаблон, подмешивать в inline `<style>` и в атрибут.
3. Заменить в `frontend/nginx.conf` `'unsafe-inline'` на
   `'nonce-{NONCE}'` + `'strict-dynamic'`.
4. Прогнать smoke-стек и визуальные regression-тесты, т.к. часть
   сторонних компонентов может поломаться — тогда fallback через
   allowlist hash'ей.

## MFA Encryption

TOTP/WebAuthn секреты в `allauth.mfa.Authenticator.data` шифруются
`accounts.mfa_adapter.EncryptedMFAAdapter`. Ключи:

- `MFA_ENCRYPTION_KEYS` — список Fernet-совместимых ключей; первый из них
  используется для новых шифрований, остальные применяются при
  расшифровке и ротации.
- `SECRET_KEY` включается в набор ключей через
  `MFA_ENCRYPTION_INCLUDE_LEGACY_SECRET_KEY=True` (значение по умолчанию)
  ради обратной совместимости со старыми инсталляциями, где MFA секреты
  шифровались Django secret key'ом.

Если ротируете `DJANGO_SECRET_KEY`, сначала добавьте новый ключ в
`MFA_ENCRYPTION_KEYS`, запустите `manage.py reencrypt_mfa_authenticators`,
и только потом удаляйте старый secret key. Иначе существующие TOTP
секреты окажутся нерасшифровываемыми.

## Reporting

Сообщайте о vulnerabilities приватно maintainers. Не открывайте публичные
issues с credentials, exploit payloads или production data.
