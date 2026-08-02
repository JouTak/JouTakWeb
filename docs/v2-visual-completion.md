# Завершение нового дизайна JouTakWeb

## Продуктовая точка отсчёта

- `joutak.ru/` — каноническая главная ITMOcraft: сообщество, проекты, события,
  галерея и FAQ.
- `/joutak` — отдельная поверхность сервера JouTak: позиционирование, IP,
  заявка, оплата и галерея.
- `/minigames` — режимы, события и игровые материалы MiniGames.
- `/itmocraft` — совместимый старый адрес, который должен перенаправлять на
  канонический `/`, а не открывать вторую версию ITMOcraft.

## Что уже адаптировано в `dev/design-visual-fixes`

- Header, hero, gallery, event cards и footer больше не создают горизонтальный
  overflow на desktop; добавлены отдельные tablet/mobile layouts.
- Header и footer ведут в ITMOcraft через `/`; `/itmocraft` перенаправляется на
  канонический адрес.
- Calendar, News, Modex, Team и Documents показаны как честные состояния
  `disabled / скоро`, пока у них нет маршрута и законченного сценария.
- Dropdown серверов использует `menu/menuitem`, скрыт из accessibility tree в
  закрытом состоянии и явно помечает недоступный Modex.
- JouTak hero снова показывает IP, заявку и оплату проходки.
- Галерея игнорирует `#` и пустые photo sources, показывает собственные
  empty/error states, отключает бессмысленные стрелки при `0–1` фото и
  использует локальные материалы JouTak/MiniGames.
- Event CTA без реальной ссылки становится disabled, а не меняет URL на `#`.
- ITMOcraft CTA ведёт в существующую форму организаторов.
- Light/dark theme переключает реальную Gravity UI theme, сохраняется между
  загрузками и имеет русское accessible name.
- Исправлено подключение CSS-модуля ITMOcraft CTA и отсутствовавшего шрифта
  event cards.
- Auth, account, onboarding, contact, payment, confirmation/reset, session
  expired, loading и 404 теперь используют единый responsive V2 shell вместо
  смеси Bootstrap и разрозненных inline-карточек.
- Прямой `/login` получил собственный фон и безопасное закрытие на `/`, не
  выбрасывающее пользователя назад за пределы сайта; переходы через `next`
  сохраняются только для внутренних адресов.
- Платёжный экран объясняет модель взноса до формы, показывает loading state,
  даёт внешний fallback и не позволяет iframe автоматически прокрутить
  пользователя мимо вводного блока.
- Контакты представлены как самостоятельные понятные destinations с описанием
  назначения Telegram, VK и Discord, а не как ряд не подписанных иконок.

## Что осталось инженерам

### P0 — до расширения rollout

1. Привести backend/frontend registry к одной фактической схеме
   `site_*_version`. Сейчас frontend registry всё ещё описывает часть старых
   имён, а `site_header_version`/`site_footer_version` объявлены variant-флагами
   с boolean-набором допустимых значений. Изменение надо делать отдельной
   миграцией с аудитом существующих definitions, rules и overrides.
2. Заменить hardcoded `landingContent.js` на versioned content payload:
   event dates/statuses, registration URLs, gallery groups, alt-тексты и CTA.
3. Перенести gallery assets в контролируемое хранилище/CDN и добавить
   pre-deploy проверку `200 + image/* + ненулевой размер`. В payload не должны
   попадать `#`, design placeholders и временные ссылки без срока жизни.
4. Проверить единый V2 shell на реальном authenticated-профиле для всех
   вариантов MFA/passkey/session management и согласовать, должен ли Legacy
   намеренно оставаться отдельной визуальной поверхностью. Для
   `admin.joutak.ru` нужен отдельный аудит: его экраны не входят в этот frontend.
5. Добавить реальные destinations для Calendar/News/Modex/Team/Documents или
   оставить их disabled до релиза соответствующего route.
6. Проверить payment iframe: loading, blocked cookies, network error, success,
   повторная оплата и возврат на JouTak. Базовый loading и внешний fallback уже
   реализованы; cross-origin success/error по-прежнему требуют согласованного
   callback или postMessage-контракта с формой.

### P1 — visual quality и адаптивность

1. Провести screenshot regression для `360×800`, `390×844`, `768×1024`,
   `1280×720`, `1440×900` и `1920×1080`.
2. Зафиксировать layout budgets: высота header, safe-area на hero, максимальная
   ширина текста, допустимый crop background и количество строк в CTA.
3. Добавить responsive image sources (`srcset`/`sizes`) и WebP/AVIF для тяжёлых
   hero/gallery assets; сейчас отдельные PNG весят несколько мегабайт.
4. Добавить reduced-motion режим и согласовать hover/focus/pressed transitions.
5. Проверить контраст light theme: pixel-art assets нарисованы под dark surface
   и могут требовать отдельной рамки или light-варианта.
6. Добавить visual tests для long copy, длинного display name, 1/4/8 gallery
   tabs и event cards без изображения.

### P2 — эксплуатация

1. События и галерею редактировать через admin/content model без frontend
   deploy.
2. Добавить telemetry на CTA, broken image fallback, disabled-item attempts и
   переходы V2 → legacy.
3. Ввести rollout dashboard: variant, audience, page context, error rate,
   conversion и быстрый rollback.

## Что передать дизайнерам

Нужен не один desktop-макет, а набор component variants и переходов.

| Поверхность       | Обязательные варианты                                                                      |
| ----------------- | ------------------------------------------------------------------------------------------ |
| Header            | desktop/tablet/mobile; guest/profile/loading; dropdown open; disabled item; long nickname  |
| Mobile navigation | закрыта/открыта; server list; account actions; focus order; escape/backdrop behavior       |
| Hero              | ITMOcraft, JouTak, MiniGames; с/без notification; один/два CTA; длинный текст; safe crop   |
| Server access     | IP copy, application, payment; loading/error/success; недоступная регистрация              |
| Event card        | upcoming/open/closed/cancelled; registration external/internal; без фото; длинное описание |
| Gallery           | loading/empty/error; 1 и много фото; 1/4/8 tabs; mobile tab selector; fullscreen/lightbox  |
| Footer            | полный/сокращённый; disabled/soon; legal links; mobile stacking                            |
| Auth/account      | login, signup, MFA, reset, onboarding, security, session-expired в V2 shell                |
| System            | route loading, section error, offline, maintenance, 404 и access denied                    |

### Формат handoff

1. Figma components с Auto Layout, variants и понятными names, а не только
   flattened page frames.
2. Variables/tokens: colors, typography, spacing, radii, borders, shadows,
   breakpoints и motion duration/easing.
3. Для каждой страницы — frames минимум на `390`, `768`, `1280` и `1440`.
4. Prototype links для dropdown, mobile menu, gallery, event registration,
   auth modal и возврата после payment.
5. Content sheet: финальные тексты, CTA labels, destinations, даты/statuses,
   alt-тексты, asset owner и дата актуальности.
6. Asset manifest: source file, export size, format, transparent background,
   crop/focal point и максимальный вес.
7. Отдельная страница `States` с loading/empty/error/disabled/focus/hover/
   pressed/success — эти состояния обязательны для приёмки наравне с happy path.

## Критерий готовности V2

V2 можно расширять за пределы tester group, когда:

- все видимые controls либо завершают сценарий, либо явно disabled;
- на основных маршрутах нет broken images и горизонтального scroll;
- бизнес-действия JouTak и MiniGames не теряются относительно legacy;
- shell и переходы согласованы на публичных, auth и account routes;
- desktop/tablet/mobile проходят visual regression;
- flag OFF возвращает полноценный legacy без потери сессии и данных;
- у контента есть владелец, срок актуальности и безопасный fallback.
