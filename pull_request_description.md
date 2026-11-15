# Устойчивость регистрации к сбою почты: очередь писем и подтверждение позже

Сбой почтового сервера больше не мешает регистрации, входу и работе с профилем. Письма подтверждения и восстановления пароля отправляет фоновый обработчик (`django-q`, брокер ORM). Подробности и инструкция: `docs/email-queue.md`.

## Что изменилось

**Очередь и доставка**
- В очередь кладётся только id записи `EmailVerificationTask`. Ключ подтверждения и токен сброса пароля создаются в момент отправки: ссылка действительна даже после долгого ожидания, а токены не попадают ни в очередь, ни в логи.
- Повторы при временной ошибке с растущей паузой (1 мин, 2, 4, ... до часа); число попыток и паузы задаются в настройках. Постоянная ошибка или исчерпанные попытки переводят задачу в статус `error`.
- Одно письмо отправляется один раз при нескольких параллельных обработчиках (аренда записи атомарным UPDATE / `locked_until`); обработчик, упавший посреди попытки, подхватывается диспетчером после истечения аренды.
- Повторные запросы не создают пачку писем: пока письмо в очереди, возвращается его текущий статус; между письмами действует пауза (`EMAIL_RESEND_COOLDOWN_SECONDS`).
- Письмо отменяется (`cancelled`) при подтверждении, замене и удалении адреса, а также удалении аккаунта.

**Доступ и API**
- `AccountStatusService.require_email_verified(user)`: 403 `EMAIL_VERIFICATION_REQUIRED`, если основной адрес не подтверждён; сбой почты подтверждённых пользователей не ограничивает.
- `POST /api/account/email/resend`: 200 со статусом и `next_allowed_at`, 400 (`EMAIL_ALREADY_VERIFIED`, `EMAIL_ADDRESS_MISSING`), 401, 429 (`EMAIL_RESEND_COOLDOWN`, `retry_after_seconds`, `next_allowed_at`, `Retry-After`). Логика вынесена в сервисный слой.
- `email_delivery` (`status`, `next_attempt_at`, `next_allowed_at`, `is_smtp_down`) отдают `/api/account/status` и `/api/auth/me`. Флаг `is_smtp_down` отличает недоступность почты от штатного ожидания.
- Смена email и восстановление пароля также идут через очередь; публичный ответ на запрос сброса не зависит от существования аккаунта.

**Инфраструктура**
- Сервис `worker` (`manage.py qcluster`) добавлен в `docker-compose.stack.yml` (в `compose.yaml` для разработки он уже настроен).
- Расписание `accounts-email-dispatch` создаётся автоматически при выполнении команды `migrate`.

## Миграции (`core`)

| Миграция | Что делает |
|---|---|
| `0007_emailverificationtask` | Таблица `EmailVerificationTask` |
| `0008_emailverificationtask_kind_cancelled` | Поле `kind`, статус `cancelled` |
| `0009_emailverificationtask_retry_fields` | Поля `attempts`, `last_error`, `locked_until` |
| `0010_emailverificationtask_next_allowed_at` | Поле `next_allowed_at` |

Данных, требующих переноса, нет. После выката выполняется обычный `migrate` (он же создаёт расписание повторов).

## Как запускать обработчик

Без обработчика письма копятся в очереди и не уходят.

- Docker dev: `docker compose up --build` (сервис `worker`).
- Production (Swarm): сервис `worker` в `docker-compose.stack.yml`; настройки `EMAIL_*` берутся из `.env.production`.
- Без Docker: `uv run python backend/manage.py qcluster --settings backend.settings.dev`.

Новые переменные окружения: `EMAIL_DELIVERY_MAX_ATTEMPTS`, `EMAIL_DELIVERY_BACKOFF_BASE_SECONDS`, `EMAIL_DELIVERY_BACKOFF_MAX_SECONDS`, `EMAIL_DELIVERY_LEASE_SECONDS`, `EMAIL_RESEND_COOLDOWN_SECONDS`.

---

## Проверка и результаты тестирования

Проверена сквозная работа очереди, планировщика и изоляции отправки в контейнерах Docker:

### 1. Автоматическое расписание и диспетчер
Проверена автоматическая регистрация расписания повторов в БД при миграции:
```bash
docker compose exec backend python manage.py shell -c "from django_q.models import Schedule; print(Schedule.objects.filter(name='accounts-email-dispatch').values('name', 'func', 'minutes'))"
# Output: <QuerySet [{'name': 'accounts-email-dispatch', 'func': 'accounts.tasks.dispatch_due_emails', 'minutes': 1}]>
```
Воркер регулярно поднимает задачу каждые 30 секунд:
```text
worker-1 | Process-... создал задачу friend-nitrogen-louisiana-kitten по расписанию [accounts-email-dispatch]
worker-1 | Process-... выполняет friend-nitrogen-louisiana-kitten «accounts.tasks.dispatch_due_emails» [accounts-email-dispatch]
worker-1 | Обработано «accounts.tasks.dispatch_due_emails» (friend-nitrogen-louisiana-kitten)
```

### 2. Отложенная сборка свежих токенов (Deferred Generation)
Проверена генерация нового валидного токена при повторном запросе отправки.
* Первоначальная ссылка (11:54:00):
  `http://localhost:5173/confirm-email?key=OQ%3A1xOw2a%3A...`
* Свежая ссылка после повторного триггера (11:57:49):
  `http://localhost:5173/confirm-email?key=OQ%3A1xOw6H%3A...`

Логи воркера подтверждают изолированную отправку через процесс `django-q`:
```text
worker-1 | Process-... выполняет timing-jersey-xray-uncle «accounts.tasks.send_email_task»
worker-1 | Content-Type: multipart/alternative;
worker-1 | To: admi@yandex.ru
worker-1 | Обработано «accounts.tasks.send_email_task» (timing-jersey-xray-uncle)
```

### 3. Проверка статуса в БД после перехода по ссылке
```bash
docker compose exec backend python manage.py shell -c "
from allauth.account.models import EmailAddress
addr = EmailAddress.objects.filter(email='admi@yandex.ru').first()
print(f'Email: {addr.email}, Verified: {addr.verified}')
"
# Output: Email: admi@yandex.ru, Verified: True
```

### 4. Защита от повторной отправки (400 Bad Request)
Повторный запрос для уже подтверждённого адреса отклоняется:
```bash
docker compose exec backend python manage.py shell -c "
from django.contrib.auth import get_user_model
from accounts.services.email_verification import EmailVerificationService
User = get_user_model()
u = User.objects.get(username='admi')
EmailVerificationService.resend(None, u)
"
# Output: ninja.errors.HttpError: 400 EMAIL_ALREADY_VERIFIED
```

### 5. Валидация гардиана защищённых действий
```bash
docker compose exec backend python manage.py shell -c "
from django.contrib.auth import get_user_model
from accounts.services.account_status import AccountStatusService
User = get_user_model()
u = User.objects.get(username='admi')
AccountStatusService.require_email_verified(u)
print('Гардиан пройден: доступ к защищённым ресурсам разрешён.')
"
# Output: Гардиан пройден: доступ к защищённым ресурсам разрешён.
```

---

## Чеклист успеха

- [x] При отключённом SMTP можно зарегистрироваться, войти и открыть профиль
- [x] После восстановления сервиса письмо отправляется без действий пользователя
- [x] Повторные запросы не создают пачку писем
- [ ] Прямой вызов API не позволяет обойти проверку почты для проходки (см. ниже)
- [x] Пользователи с подтверждённой почтой продолжают работать во время сбоя
- [x] Подтверждение email снимает почтовое ограничение
- [x] Проверены перезапуск обработчика, смена адреса, истёкшая ссылка и окончательная ошибка отправки
- [x] Добавлены тесты и инструкция по запуску и проверке очереди

## Что не вошло

- **Проходка.** Эндпоинтов оформления и выдачи проходки в бэкенде нет, поэтому проверку подтверждения почты негде подключить. Готов и покрыт тестами вызов `AccountStatusService.require_email_verified(user)`; к эндпоинту проходки он подключается одной строкой. Пункт чеклиста про проходку остаётся открытым.
- Подтверждение по одноразовому коду (`..._BY_CODE_ENABLED`) не поддерживается: код нельзя создать заново при отправке.
- Письма без секретов (например, «аккаунт не найден») повторяются до 3 раз.

## Согласование с фронтендом

Поля и ответы описаны в `docs/email-queue.md`, раздел «Контракт API для фронтенда».
- [ ] Согласовано с: **[имя исполнителя фронтенда]**

@m4tveevm, прошу на ревью.