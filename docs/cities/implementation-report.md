# Результат локального MVP

Работа остаётся в текущем working tree для одного будущего PR. Коммиты, push,
удалённый PR, production migrations и включение production flags не выполнялись.
Исходная архитектура исследована и proposal/ADR написаны до реализации.

## Реализовано

- Отдельный публичный CommunityProfile поверх неизменённого core.UserProfile;
  настройки имени, bio, загружаемого аватара и видимости. Legacy Minecraft/VK/ИТМО
  редактируются отдельными короткими диалогами через существующий account API. Email/ISU не входят в публичные
  schemas. Legacy accounts не публикуются автоматически.
- Generic Community/CommunityMembership и независимые City/CityMembership.
  Несколько городов на пользователя; role отличается от должности; owner_id нет.
- Каталог с поиском, recruitment filter и pagination, структурированная страница
  города, представители с privacy-aware профилями, координаты, контакты/ссылки,
  Markdown без raw HTML, fallback изображений.
- Кабинет с приглашениями и карточками городов; отдельные сообщества и профиль.
  Пункт «Профиль» открывает публичное представление. Безопасность — сгруппированные
  способы входа без дубля профиля и второй навигации. Существующие security,
  onboarding и complete-profile routes сохранены. Bootstrap не добавлен в новые
  surfaces; используется Gravity UI и общий visual language портала.
- Короткие редакторы прямо со страницы города, preview и защита несохранённых
  изменений. Жители и история — вкладки города; история загружается по запросу.
  Приглашения с обязательным согласием адресата, отзывом и сроком 14 дней.
  До принятия членства нет; принятие даёт только роль жителя. Управление правами
  после принятия с подтверждением опасных действий.
- Moderator console: создание с первым manager, фильтры статусов, публикация,
  архивирование/восстановление и история. Emergency city admin — read-only,
  чтобы изменения проходили через audited services.
- Atomic audit/revisions, защита последнего manager, concurrent demotion/deletion,
  scoped membership lookups, bounded role inputs. Moderator определяется через
  существующий Django permission, а не отдельный admin flag на User.
- BlueMap deeplink по фактически проверенному формату deployment; URL формирует
  backend, editor не задаёт origin. Нет iframe/зависимости от доступности карты.
- 6 default-off rollout flags, idempotent community seed, изолированный demo seed.
- По дополнительному запросу: `/players`, поиск по доступным полям, подписки,
  круг общения, Discord/Telegram/VK контакты с выбором аудитории. Профили и
  карточки используют визуальный референс PR #36; sharing — кнопка-иконка ссылки.
  [Решения и ограничения](player-connections.md).

## Изменённые области

| Область | Основные файлы/каталоги |
| --- | --- |
| Public identity | backend/profiles; frontend/components/profile; pages/profile, pages/account |
| Community domain | backend/communities; frontend/components/communities; pages/communities |
| City governance | backend/cities; frontend/components/cities; pages/cities, pages/moderation |
| API clients | frontend/src/services/api/{profiles,communities,cities,moderation}Api.js |
| Shell / rollout | App.jsx, main.jsx, existing headers/navigation, features/hub, featureflags/registry.py |
| Integration | backend URLs/settings, account deletion 409 contract, OpenAPI checker |
| Compatibility fix | backend/backend/admin_site.py: allauth request ContextVar instead of global mutation |
| QA | backend/cities/tests, accounts/tests/test_city_deletion.py, CityHub.test.jsx, e2e/community-hub.spec.js |
| Documentation | architecture/domain-model/rbac/adr/rollout/testing under docs/cities; README; .env.example |

## Миграции

`profiles/0001_initial`, `communities/0001_initial`, `cities/0001_initial`;
`profiles/0002_alter_communityprofile_avatar_url` и
`cities/0002_alter_city_cover_url_alter_city_logo_url_and_more` добавляют
приглашения и поддержку относительных media references без потери URL.
User и core.UserProfile не меняются.
`profiles/0003_communityprofile_connections_visibility_and_more` добавляет
ProfileFollow, ProfileContact и закрытую по умолчанию видимость круга общения.
Обратные migrations технически возможны, но удалят новые данные; operational
rollback делается flags, не drop tables. MigrationExecutor проверяет upgrade
со старой записью UserProfile; PostgreSQL также проходит этот сценарий.

## API и маршруты

Полная карта — [architecture.md](architecture.md); OpenAPI `/api/openapi.json`
остаётся source of truth. Основные namespaces: profiles, communities, cities,
account/memberships, moderation/cities. Self/public schemas разделены; PATCH
города требует `version`; все known inputs ограничены и unknown fields запрещены.

UI: `/account`, `/account/profile`, `/account/communities`, `/u/:username`,
`/communities`, `/communities/:slug`, `/cities`, `/cities/:slug`,
`/cities/:slug/manage`, `/moderation/cities`. Security/onboarding URLs сохранены.

## Права и rollout

Resident читает; Representative редактирует narrative/contacts/presentation;
Manager дополнительно управляет facts/location/roster и representatives.
Назначение/снятие managers, lifecycle и emergency override — platform moderator
(`cities.moderate_city`) или superuser. `is_staff` сам по себе недостаточен.
Последний manager защищён также при account deletion и community suspension.

Flags: `community_profiles_ui`, `communities_ui`, `cities_ui`,
`cities_management_ui`, `cities_moderation_ui`, `cities_map_integration`.
Все default-off. Backend проверяет flags и права независимо от frontend.
BFF bootstrap отдаёт flags; списки городов/жителей в глобальный viewer не добавлены.
Игроки, подписки и контакты используют тот же `community_profiles_ui`.

## BlueMap

Проверенный пример:
`https://map.joutak.ru/#joutak:1240:0:-438:1500:0:0:0:1:flat`.
Настройки: `ITMOCRAFT_MAP_BASE_URL`, `ITMOCRAFT_MAP_IDS`. Проверен map ID `joutak`.
При единственной настроенной карте и основном мире backend выбирает проверенный
map ID; в UI нет технического поля. Можно вставить ссылку viewer: backend
проверяет origin/формат, извлекает X/Z и игнорирует высоту камеры. Нет location — нет CTA.
Ссылки открываются с `noopener noreferrer`. Marker sync и authoritative source
описаны в [ADR](adr.md), синхронизация сейчас не запускается.

## Проверки

Команды и воспроизводимая PostgreSQL-проверка — [testing.md](testing.md).

- Ruff, Bandit, Django system checks и отсутствие неприменённых model changes.
- Frontend/OpenAPI checker: 38 вызовов, включая nested membership endpoints.
- Полный backend suite после UX-переработки: 248 passed, 15 subtests passed,
  2 SQLite concurrency skips. PostgreSQL: 48 passed, включая новую гонку принятия
  приглашения. Финальная проверка invitation/media API и квоты: 10 passed,
  14 subtests passed. Теперь SQLite пропускает три PostgreSQL-only гонки.
- Frontend `npm run check`: lint, format, stylelint, 80 Vitest tests, production build.
- Все 6 Playwright tests: новые guest journeys, responsive/axe и прежние страницы.
- Реальный браузер + локальная БД: login → account → city management → preview →
  save → revision/audit, предупреждение о несохранённых правках. Live HTTP smoke
  проверил все четыре роли, privacy, forged roles, IDOR, version conflict,
  last manager, создание/публикацию/архив. Тестовые правки Альфы восстановлены.
- Повторный demo seed сохраняет существующий пароль и контент.

Production npm audit policy и pip-audit проходят. Обнаруженные baseline
advisories закрыты обновлениями React Router 7.18.4, fast-uri 3.1.8, Django
5.2.17, cryptography 50.0.1 и sqlparse 0.6.0; совместимый fido2 — 2.2.1.
Lockfiles и generated requirements обновлены. Проверки не ослаблялись.
Источники, точные границы audit gate и первоначальный browser timeout описаны
в [testing.md](testing.md).

## Ограничения и отложенная работа

- History есть; автоматического rollback нет. Review workflow не включён:
  изменения опубликованного города появляются сразу.
- Community membership onboarding/management пока через existing Django admin;
  self-service вступления и join requests не добавлены.
- Images: PNG/JPEG/WebP ≤3 МБ и ≤16 MP, re-encode в WebP без metadata,
  существующее Django storage, случайные имена. Публичны по ссылке; upload quota
  по аккаунту. Непривязанные файлы после отмены формы пока сохраняются.
- Public roster показывает только разрешённые видимостью профили и связи.
  Moderator override с причиной доступен API; обычный UI предлагает transfer.
- Несохранённые profile/city forms предупреждают при SPA-переходе, Back и
  закрытии/reload вкладки. Сохранение не затирает текст, введённый пока шёл запрос.
- Username, изменённый emergency admin, меняет profile URL; aliases не добавлены.
- Прямые operator SQL/QuerySet.update не являются governance API. Особенно при
  деактивации пользователя нужно сначала передать manager duties.
- Document titles есть; полноценный SSR/OG crawler rendering не добавлен.
- Метрики не вводились отдельным стеком. Structured mutation logs содержат
  city/actor/action/result; audit остаётся отдельными product data. Будущие
  counters можно поставить на policy denial, detail query и mutation services.
- Tasks/Spaces/economy/elections/server permissions/notifications/marker sync
  остаются вне MVP. UUID binding рекомендуется до server membership sync.

## Локальная проверка и следующая итерация

Открыть http://127.0.0.1:5174/cities. Backend: 127.0.0.1:8011. Demo DB:
`.local/community-hub.sqlite3`. Текущие credentials — `.local/demo-access.txt`
(ignored, не входят в PR). Personas и полный manual QA — [rollout.md](rollout.md).
Контейнеры demo пересобраны; SQLite и media сохраняются в `.local`.
Для параллельных session-запросов SQLite использует IMMEDIATE и timeout 20 секунд.
Другие Docker-стенды этой переработкой не запускались.

Проверка каждого пункта исходного ТЗ — [acceptance-audit.md](acceptance-audit.md).
Сначала maintainer review текущего локального MVP и dependency audit fixes;
после одобрения — один PR. Отдельно можно спланировать join requests, безопасный
revision rollback, Minecraft UUID и BlueMap marker adapter. Они автоматически
не реализованы и не включены.

## Проверено по пользовательскому фидбэку

См. [ux-revision.md](ux-revision.md). В реальном браузере manager отправил
приглашение в Бету; recipient увидел его в кабинете и принял, получил toast и
карточку города. Затем тестовое членство снято через подтверждение управляющего,
счётчик обновился, все три действия сохранились в истории. Demo-персоны
возвращены к исходному составу; текущая браузерная учётка — hub_manager.
Проверены загрузка PNG и preview, импорт BlueMap, короткий редактор, меню профиля,
отдельная безопасность, экран телефона 390 px без горизонтального переполнения.

Новые Discord/Telegram/VK контакты проверяются по провайдеру. Произвольные
website/other больше не принимаются; прежние записи доступны для чтения.
Не добавлены: блоковый конструктор городских страниц, общая система уведомлений,
границы/площади и регулярная синхронизация BlueMap. Для границ нужен контракт
сопоставления регионов и городов.

## Поиск игроков и референс PR #36

Добавлены ProfileFollow/ProfileContact, migration 0003 и шесть typed endpoints;
клиент `playersApi.js`, `/players`, карточки игроков, круг общения, короткий
редактор контактов и компактная кнопка ссылки. Подписки и контакты закрыты по
умолчанию. Email/ISU/дата рождения из демонстрационного референса не публикуются;
никаких внешних запросов за fallback-аватаром нет. Chat, notifications и графовый
редактор не добавлены. Правила видимости и API — [player-connections.md](player-connections.md).

Проверки этой итерации:

- Полный backend: 258 passed, 3 PostgreSQL-only skips, 17 subtests. После последнего
  исправления приоритета приватного VK отдельно прошли все 10 profile tests.
- OpenAPI: 44 frontend Ninja calls. Ruff/Bandit/Django checks прошли;
  model drift отсутствует. Migration 0003 применена к существующей demo DB.
- `npm --prefix frontend run check`: 88 tests, lint/format/stylelint/build.
  После изоляции clipboard mock дополнительно прошли 8 tests игроков.
- Полный Playwright: 7 passed; после кнопки-иконки повторные 4 Hub tests прошли.
  Один промежуточный запуск потерял city heading во время пересборок; повтор
  после их завершения прошёл без изменения проверок. Размеры: 320/768/1440 px,
  axe и отсутствие горизонтального переполнения.
- Живой локальный стенд: guest search → profile → login return → follow → own
  following → unfollow. Закрытый фиктивный Discord сохранён, проверен из отдельной
  guest session и удалён. Проверены копирование ссылки/toast и mobile 390 px.
  Тестовые подписки и контакты восстановлены; demo roles не менялись.

Начало проверки: http://127.0.0.1:5174/players. Инструкции и существующие четыре
демо-персоны — [rollout.md](rollout.md). Изменения остаются локальными.

Дополнительное уточнение гостевого UX: профиль открывается по аватару и имени без отдельной кнопки,
а призыв «Войти и подписаться» удалён из карточек и публичного профиля.
Подписка показывается только вошедшим пользователям. Гостевой сценарий
закреплён в существующих component и browser tests; серверные права не менялись.

Следующее уточнение: карточки каталога/подписок показывают только аватар, ник и
доступные строки «Город — должность/роль», без повторного имени, Minecraft badge
и bio. `PlayerOut.cities` добавлено без миграции; используется общая policy
видимости членства, только активные города/членства и четыре запроса на страницу.
Шапка профиля также без повторов: описание и городские статусы внизу,
ссылка «Игроки» и иконка копирования справа сверху. Проверены реальные демо-данные
и экран 390 px. Проверки: 88 frontend tests/build/lint/stylelint, 4 Hub browser
tests, 11 profile backend tests, OpenAPI/Ruff/Bandit. Остальные 46 city tests и
14 subtests прошли; три PostgreSQL-only теста пропущены на SQLite. В новых
fixtures исправлено обязательное описание активного города; проверки БД сохранены.


## Карточки профиля и взаимные подписки

Имя возвращено под ником в самом профиле; каталог остался компактным. Вместо
вкладок — стаж, дата первого входа, карточки подписчиков и друзей с сетками
аватаров. Друзья вычисляются из двух встречных подписок, обычные подписчики
исключают взаимные связи. Обе карточки обновляются после follow/unfollow.

По последнему уточнению пользователя общая дата **01.01.2026** установлена
по умолчанию всем существующим и новым community profiles через `profiles/0004`;
пометок об ожидании сервера нет. Серверного источника пока нет. Стаж считается
в календарных днях, склонение выполняет pymorphy3; поле защищено от self-edit и
подчиняется Minecraft visibility. Подробности — [player-connections.md](player-connections.md).

Проверки: 22 backend tests + 13 subtests, включая upgrade существующего профиля;
91 frontend test, lint/format/stylelint/build; 5 Hub Playwright scenarios с
axe и размерами 320/768/1440; OpenAPI 44 calls; Ruff/Bandit; migration drift нет.
Production dependency audit: известных уязвимостей не обнаружено. Изменения
локальные, без commit/push/PR. Перед миграцией локальной demo DB сделана резервная
копия; новые demo friendship rows не навязываются существующим аккаунтам.


## Основное имя игрока и краткая дата

Единое отображение Minecraft-ник → логин → нейтральная подпись применяется к
каталогу, администрации/жителям, аватарам друзей/подписчиков, личному кабинету
и account avatar. Имя/фамилия остаётся вторичной строкой только в профиле.
Редактирование/копирование ссылки — серые иконки в этом порядке, редактирование
только владельцу; ссылки «Игроки» в шапке нет. Под стажем теперь «с 01.01.2026».

Management roster и приглашения получили optional Minecraft nickname с той же
backend visibility policy. Roster также возвращает разрешённый avatar URL.
SQL annotation и select_related исключают N+1. Username/id остаются ключами
ссылок и mutations; ввод приглашения по логину сохраняется. Миграций нет.

Проверки: 70 backend tests, 27 subtests, 3 PostgreSQL-only skips на SQLite;
92 frontend tests и полный check; 5 Hub browser scenarios; OpenAPI 44 calls;
Ruff/Bandit. Отдельно проверены скрытые nick/profile для управляющего, снятие
доступа при suspension, стабильность ссылок и число запросов на roster/invitations.
Изменения и обновлённые контейнеры остаются только локальными.
