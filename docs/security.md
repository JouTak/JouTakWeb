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

## Reporting

Сообщайте о vulnerabilities приватно maintainers. Не открывайте публичные
issues с credentials, exploit payloads или production data.
