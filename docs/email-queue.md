# Очередь писем и подтверждение почты

Письма аккаунта (подтверждение почты, восстановление пароля) отправляет
фоновый обработчик, а не запрос пользователя. Сбой почтового сервера не
мешает регистрации, входу и работе с профилем.

## Как это работает

1. Регистрация, смена email, повторная отправка или запрос сброса пароля
   создают запись `core.EmailVerificationTask` и ставят в очередь django-q
   задание только с её id. Ни ключ подтверждения, ни токен сброса, ни текст
   письма в очередь и в логи не попадают.
2. Обработчик (`manage.py qcluster`) занимает запись (аренда
   `EMAIL_DELIVERY_LEASE_SECONDS`), заново собирает письмо средствами
   allauth и отправляет. Ссылка создаётся в момент отправки, поэтому она
   действительна, даже если письмо долго ждало в очереди.
3. Временная ошибка (нет соединения, таймаут, 4xx): статус `retrying`,
   следующая попытка с растущей паузой (1 мин, 2, 4, ... до
   `EMAIL_DELIVERY_BACKOFF_MAX_SECONDS`). Повторы запускает задача
   `accounts.tasks.dispatch_due_emails`, раз в минуту.
4. Постоянная ошибка (получатель отклонён, 5xx на данные письма) или
   исчерпанные попытки: статус `error`, повторов нет. Пользователь может
   запросить письмо снова.
5. Если адрес уже подтверждён, заменён или удалён, письмо не отправляется,
   статус `cancelled`. Подтверждение, удаление адреса и аккаунта отменяют
   ожидающие письма сразу (`accounts/signals.py`).
6. Повторные запросы не создают пачку писем: пока письмо в очереди, API
   возвращает его статус; после отправки действует пауза
   `EMAIL_RESEND_COOLDOWN_SECONDS`.

Статусы: `waiting` (в очереди), `retrying` (временная ошибка, ждёт
повтора), `sent`, `error`, `cancelled`. Статус `sent` ставится только после
реальной отправки, приём в очередь им не считается.

## Запуск обработчика

Без запущенного обработчика письма копируются в очереди и не уходят.
Очередь хранится в базе (брокер ORM), поэтому задания переживают перезапуск
приложения и обработчика. Расписание `accounts-email-dispatch` создаётся
автоматически командой `migrate`.

- Docker (dev): сервис `worker` в `compose.yaml` поднимается вместе со стеком
  (`docker compose up --build`).
- Docker Swarm (production): сервис `worker` в `docker-compose.stack.yml`,
  одна реплика по умолчанию. Реплик может быть несколько: одно письмо
  отправляется один раз. SMTP-настройки (`EMAIL_*`) берутся из
  `.env.production`, как у `backend`.
- Без Docker: `uv run python backend/manage.py qcluster --settings
  backend.settings.dev` в отдельном терминале рядом с `runserver`.

## Настройки (переменные окружения)

| Переменная | По умолчанию | Смысл |
|---|---|---|
| `EMAIL_DELIVERY_MAX_ATTEMPTS` | 24 | число попыток (около 22 часов) |
| `EMAIL_DELIVERY_BACKOFF_BASE_SECONDS` | 60 | пауза после первой ошибки |
| `EMAIL_DELIVERY_BACKOFF_MAX_SECONDS` | 3600 | потолок паузы |
| `EMAIL_DELIVERY_LEASE_SECONDS` | 180 | сколько обработчик «владеет» письмом |
| `EMAIL_RESEND_COOLDOWN_SECONDS` | 60 | пауза между письмами на один адрес |
| `EMAIL_TIMEOUT` | 10 | таймаут SMTP (production) |

`ACCOUNT_EMAIL_VERIFICATION` должен оставаться `optional`: при `mandatory`
вход без подтверждения блокируется. Вход подтверждением по коду
(`ACCOUNT_EMAIL_VERIFICATION_BY_CODE_ENABLED`) эта схема не поддерживает:
одноразовый код нельзя создать заново при отправке.

## Как проверить при отключённой почте

Автоматически (регистрация, вход, профиль, смена email и сброс пароля при
сломанном SMTP, плюс отправка после восстановления):

```bash
uv run pytest backend/accounts/tests/test_email_access.py \
  backend/accounts/tests/test_email_queue.py \
  backend/accounts/tests/test_email_retry.py \
  backend/accounts/tests/test_email_resend.py -q
```

Вручную, без Docker. Создайте файл `backend/backend/settings/local_smtp_down.py`
(не коммитить):

```python
from .dev import *  # noqa: F403

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "127.0.0.1"
EMAIL_PORT = 1  # там никто не слушает: соединение отклоняется
EMAIL_TIMEOUT = 5
```

В двух терминалах (паузу повторов можно сократить переменной):

```bash
export EMAIL_DELIVERY_BACKOFF_BASE_SECONDS=5
uv run python backend/manage.py migrate --settings backend.settings.local_smtp_down
uv run python backend/manage.py runserver 127.0.0.1:8000 --settings backend.settings.local_smtp_down
uv run python backend/manage.py qcluster --settings backend.settings.local_smtp_down
```

1. Зарегистрируйтесь и войдите: профиль открывается, `email_verified` равен
   `false`, `email_delivery.status` сначала `waiting`, затем `retrying` с
   `is_smtp_down: true`.
2. Остановите и снова запустите `qcluster`: записи и очередь остаются в базе,
   повторы продолжаются.
3. Верните почту: остановите оба процесса и запустите `qcluster` с
   `--settings backend.settings.dev` (письма печатаются в консоль). Накопившиеся
   письма уходят сами в пределах паузы повтора, статус становится `sent`.

Состояние очереди:

```bash
uv run python backend/manage.py shell -c "
from core.models import EmailVerificationTask as T
for t in T.objects.order_by('-updated_at')[:20]:
    print(t.id, t.kind, t.status, t.attempts, t.last_error, t.next_attempt_at)
"
```

## Эксплуатация и логи

- Сбой доставки пишется событием `email_delivery.failed` с полями
  `tracker_id`, `mail_kind`, `attempt`, `error_class`, `permanent`, `final`.
  Адреса, текст письма и токены в логи не попадают.
- Письма не уходят: проверьте, что `worker` запущен, что расписание
  `accounts-email-dispatch` есть (`django_q.Schedule`), что заданы `EMAIL_*`
  и что записи не в `error` (причина в `last_error`).
- Письма без секретов (например, «аккаунт не найден») ставятся в очередь
  готовыми и повторяются не более 3 раз (`Q_CLUSTER["max_attempts"]`).

## Контракт API для фронтенда

- `GET /api/account/status`, `GET /api/auth/me`: `email_verified` (bool) и
  `email_delivery` (`null` для подтверждённого адреса или если письма не
  было) с полями `status` (`waiting`, `retrying`, `sent`, `error`,
  `cancelled`), `next_attempt_at`, `next_allowed_at`, `is_smtp_down`.
  `is_smtp_down: true` означает, что почтовый сервис недоступен;
  `waiting` при `false` это обычное ожидание в очереди.
- `POST /api/account/email/resend`:
  - 200, `delivery` с текущим статусом и `next_allowed_at`. Если письмо уже
    в очереди, новое не создаётся;
  - 400, `error_code`: `EMAIL_ALREADY_VERIFIED` или `EMAIL_ADDRESS_MISSING`;
  - 401: нет сессии;
  - 429: слишком рано. Поля `error_code: EMAIL_RESEND_COOLDOWN`,
    `retry_after_seconds`, `next_allowed_at` и заголовок `Retry-After`.
- Действия, требующие подтверждённой почты, отвечают 403 с
  `error_code: EMAIL_VERIFICATION_REQUIRED`. На сервере проверка делается
  вызовом `AccountStatusService.require_email_verified(user)`.
