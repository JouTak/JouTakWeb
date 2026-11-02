# Проверка выполнения исходного ТЗ

Дата: 21 сентября 2026. Проверяется текущий локальный worktree, а не production.
Ничего не отправлено в GitHub; remote PR, push и deployment не выполнялись.
Пункты ниже сохраняют номера исходного master prompt. Диапазон означает, что
вывод относится к каждому входящему в него пункту. Опциональные варианты и
будущие этапы не объявляются реализованными.

## Доказательства

- **Архитектура:** [architecture](architecture.md), [ADR](adr.md),
  [модель с диаграммой](domain-model.md), [RBAC](rbac.md).
- **Backend:** `backend/profiles`, `backend/communities`, `backend/cities`;
  модели, migrations/0001_initial, policies, services, queries, schemas, API,
  admin, seed commands. Интеграция в settings/urls, accounts и feature registry.
- **Frontend:** `frontend/src/pages/{account,profile,communities,cities,moderation}`,
  одноимённые feature components, `components/hub`, `features/hub`, domain clients.
- **Регрессия:** полный backend 239 passed + 3 subtests; 2 SQLite-only skips
  проверены отдельным PostgreSQL-прогоном (37 passed). Frontend 64 passed,
  6 Playwright tests, build/lint/format/stylelint. Подробности и команды в
  [testing](testing.md). Ruff/Bandit/OpenAPI/Django и production audits проходят.
- **Работающий demo:** frontend `http://127.0.0.1:5174`, backend
  `http://127.0.0.1:8011`, изолированная `.local/community-hub.sqlite3`.
  Live HTTP smoke всех четырёх ролей записан в `.local/live-smoke-results.json`.
  Browser QA подтвердил account/security, город, редактор/preview/save/history
  и предупреждение об уходе без сохранения. Это локальные данные.

## Карта требований

| № | Итог и конкретное подтверждение |
| --- | --- |
| 0 | Discovery выполнен до реализации: обязательные пути, conventions, API, UserProfile, BFF, auth, flags, admin/history, tests и GitHub PR/issues описаны в architecture. |
| 1 | React/Gravity, domain API clients, route pages и тонкие Ninja routers; новые models не добавлены в core. |
| 2 | Account → profile → memberships → community/city → governance/map связаны API и UI; live smoke A–H ниже. |
| 3 | Scope ограничен identity/community/city foundation; task/workflow/economy engine отсутствуют. |
| 4 | Реализована карта URL из architecture; account/security сохранён отдельным маршрутом. |
| 5 | AccountDashboard показывает identity и списки communities/cities с ролями; multi-city manager есть в demo. |
| 6 | AccountNav: overview/profile/communities/security. Notifications/apps — будущие разделы. |
| 7 | CommunityProfile отдельный от security Account; публичный UI `/u/:username`. |
| 8 | Display name/bio/avatar, legacy Minecraft/VK/ITMO, memberships/roles/joined date; core.UserProfile не меняется. |
| 9 | PUBLIC/COMMUNITY/PRIVATE обеспечены backend policies/serializers, включая связь в leadership; отдельные public/self schemas. |
| 10 | ProfileHero + MembershipCards, публичная identity и переходы к городам. |
| 11 | Generic Community с данными, media references, status/visibility/timestamps. |
| 12 | CommunityMembership, четыре статуса, уникальность user/community. |
| 13 | Один scoped role на membership выбран и документирован; community-role не даёт platform powers. |
| 14 | City FK → Community, отдельная сущность с publication/content/metadata. |
| 15 | Lifecycle draft/active/archived отделён от recruitment open/limited/closed, DB checks. |
| 16 | Фиксированный typed CityContent, единая CityPresentation; произвольных page schemas нет. |
| 17 | Hero, media fallback, recruitment, map CTA; founding/region/population/freshness в facts. |
| 18 | Структурированные facts и recruitment; optional language хранится в модели/editor. |
| 19 | Markdown textarea + react-markdown: raw HTML выключен, ссылки проверяются. |
| 20 | CityContact: bounded type/label/HTTPS URL/visibility/order, серверная валидация. |
| 21 | Контакты и внешние ссылки объединены в один typed entity, как допускает ТЗ. |
| 22 | Location embedded в City: world, integer x/z/y, map_id, marker reference; X/Z атомарная пара. |
| 23 | Backend canonical URL, CityMapCard/hero CTA, новая вкладка и noopener/noreferrer. |
| 24 | BlueMap iframe отсутствует. |
| 25 | Карточка мира/координат/CTA, без карты работает. |
| 26 | ADR future marker adapter: authoritative DB, upsert/remove, retries/failure isolation/backlink. Sync не запускается. |
| 27 | CityMembership с четырьмя статусами и joined/left timestamps. |
| 28–29 | Resident/Representative/Manager и их полномочия реализованы CityPolicy + mutation services; tests матрицы. |
| 30–31 | Human-readable position строкой в membership, не source авторизации; отдельная таблица опциональна и не нужна MVP. |
| 32 | Централизованная CityPolicy и scoped services, не owner checks в routers. |
| 33 | Django permission cities.moderate_city + superuser; staff сам по себе не moderator. |
| 34 | RBAC таблица + service/API tests; manager elevation в MVP строже — platform-only. |
| 35 | Backend повторно проверяет permission на каждом mutation независимо от capability UI. |
| 36 | Guest catalog, CityCard, search/recruitment, pagination; DB filtering. |
| 37 | CityPresentation: hero/about/facts/leadership/map/contacts/how-to-join; audit history в manage, не публичный feed. |
| 38 | Leadership: разрешённые avatar/name/nick/position/profile link; скрытая identity деградирует безопасно. |
| 39 | Публичный список active residents paged и фильтруется profile/membership visibility; management roster отдельно защищён. |
| 40 | How-to-join narrative/contact CTA; join request engine не добавлен. |
| 41–44 | Короткие контекстные editor dialogs; жители и lazy history — вкладки CityDetail. /manage сохранён как redirect. |
| 45 | Dirty/saving/saved/error, version conflict сохраняет draft, preview; SPA/Back/beforeunload guard. |
| 46–47 | Отдельная CitiesModeration page: create, lifecycle/search/recent filters, managers/actor/visibility/updated time. |
| 48–49 | CityAuditEvent — product data с nullable actor/action/city/target membership/time/typed metadata; отдельно structured logging. |
| 50 | CityRevision: версия, actor/time, полный typed snapshot/changed fields; соседние версии дают before/after. |
| 51 | Content active city публикуется сразу; draft остаётся draft. Protected operations строже, audit/revisions атомарны. Review engine не вводился. |
| 52 | Шесть default-off flags существующего registry, server gates и phased rollout. |
| 53 | BFF bootstrap только flags/viewer shell; города и roster не загружаются в глобальный viewer. |
| 54 | City capabilities сериализованы для frontend; роль — metadata, service authority независим. |
| 55 | REST-ish namespaces без новой API версии; существующий Ninja/error/auth стиль. |
| 56 | Self GET/PATCH и public GET; `/public/{username}` предотвращает collision legacy username `me`. |
| 57 | Communities list/detail и account/memberships GET; management communities — admin. |
| 58 | Catalog/detail/own membership/roster/mutations; контакты обновляются атомарно через CityUpdate. |
| 59 | Bounded Ninja/Pydantic schemas, extra=forbid, enums, max lengths/lists, HTTPS и integer location. |
| 60 | Structured errors: denied/not-found/slug conflict/duplicate/last-manager/invalid role/location/version conflict. |
| 61 | Last manager guard; explicit moderator override с reason; service/API + PostgreSQL tests. |
| 62 | City role enum отвергает PLATFORM_ADMIN; managers не могут назначать manager; live negative checks. |
| 63 | Membership lookup включает city; чужой ID → 404, проверено live/API. |
| 64 | City slug global unique/lowercase/stable; выбор документирован, editor не меняет slug. |
| 65 | Product action archive, hard delete отсутствует; history/data сохраняются. |
| 66 | PNG/JPEG/WebP upload с ограничениями размера/pixels/quota, перекодированием и случайными именами в existing media storage; fallback. |
| 67 | Небольшие feature components, формы/поля/карточки/история разделены по ответственности. |
| 68 | Gravity UI + текущие theme tokens; новый Bootstrap не добавлен. Legacy ProfileCard переиспользуется. |
| 69 | Responsive grid/stack/forms/roster; City Playwright widths 320/768/1440, existing route matrix; account/manage визуально проверены на 375 px без overflow. |
| 70 | Headings, labelled controls, buttons/links, errors/status text, focus, alt; axe нового city surface проходит. |
| 71–72 | ResourceState, Loader, error/retry и контекстные empty states (memberships/contacts/leadership/roster/location). |
| 73 | Hidden/draft/archived для guest — uniform CITY_NOT_FOUND; UI отображает structured error. |
| 74 | q/recruitment/page, размер 24, page bound; moderation также recent_days. |
| 75 | Unique membership constraints и indexes status/user/city/role; migration/model tests. |
| 76–77 | transaction.atomic, user → city row locks; две реальные PostgreSQL connections проверяют concurrent demotion и account deletion. |
| 78 | Count через DB aggregate, без денормализации. |
| 79 | select_related/prefetch/annotation в queries; query-budget regression с несколькими leaders. |
| 80 | City services, membership_service, policies/queries отдельно от транспортных routers. |
| 81 | Audit/revisions в той же transaction; rollback-on-error test не оставляет audit. |
| 82 | Mutation/denial structured logs city/slug/actor/action/result без токенов/email/ISU/contact values. |
| 83 | Необязательные отдельные counters отложены; instrumentation points описаны в report. Существующий observability stack сохранён. |
| 84 | Threat review architecture: XSS, URL/SSRF, auth/CSRF, IDOR/escalation, enumeration, deletion. Негативные тесты. |
| 85 | Public schemas не содержат email/ISU/IP/session/moderation notes; privacy tests и live проверка. |
| 86 | Profile richness optional, legacy completion/activation не изменены. |
| 87 | Additive migrations → hidden flags → staff/beta/public; production шаги документированы, не выполнялись. |
| 88 | seed_itmocraft_community idempotent, сохраняет существующие edits. |
| 89–90 | Создание только moderator; typed form, initial manager/community membership + audit атомарно. |
| 91 | Admin зарегистрирован для всех сущностей с search/filter; city governance/history read-only, чтобы не обходить policies/audit. Emergency writes — audited API/services. |
| 92–93 | History actors/actions/field summary/versions; updated_at с locale date. Relative freshness не обязательна. |
| 94–96 | Двусторонние Profile ↔ City, breadcrumb Community → City и canonical map CTA; live A/D. |
| 97 | ItmoCraft navigation cities + account menu; management entry локально у города, не глобальный список городов. |
| 98–102 | Journeys доступны; moderator inspect history реализован. Rollback — отдельная работа, явно разрешённая пунктом 112. |
| 103 | Backend/domain/frontend/flags/seed/docs usable MVP присутствуют; evidence выше. |
| 104 | Все перечисленные non-goals оставлены вне MVP. |
| 105–106 | До кода были architecture/domain-model/RBAC/rollout, findings/assumptions и план локальных review blocks. |
| 107 | Foundation: models/constraints/migrations/admin/seed/invariants. Empty/upgrade/PostgreSQL tests проходят. |
| 108 | Read APIs guest/self; приватные данные фильтруются backend. |
| 109 | Account/profile/community UI; legacy security/onboarding URLs сохранены. |
| 110 | Catalog/detail со всеми обязательными city sections. |
| 111 | Management content/contact/location/roster/roles, audit каждого sensitive mutation. |
| 112 | Moderation + history inspection; автоматический rollback отложен согласно разрешённой границе MVP. |
| 113 | BlueMap grammar проверена на текущем deployment; точный observed URL в ADR, backend allowlist. |
| 114–117 | Future markers/tasks/join requests/server sync/UUID описаны как extension points; не реализованы автоматически. |
| 118–119 | API/service tests happy/auth/permissions/validation/not-found/conflict; имена тестов в backend/cities/tests. |
| 120 | RTL: cards, capabilities, validation/error, map/safe markdown; unsaved navigation regression. |
| 121 | OpenAPI checker расширен на nested templated paths и payload contracts; отдельные checker tests; 29 calls passed. |
| 122 | Переиспользован существующий Playwright; manual persona QA в rollout. |
| 123 | MigrationExecutor upgrade существующего UserProfile, также на PostgreSQL. |
| 124–125 | Изолированный demo seed Alpha/Beta + четыре роли; browse/edit/history/map success story пройден. |
| 126–129 | Typed CityCard/Detail, Public/SelfProfile/Memberships; account использует обычный профильный запрос, без нового BFF aggregation. |
| 130–132 | Map origin/map ID config, numeric bounds, никаких arbitrary map URLs/PostGIS/polygon editor. |
| 133 | Markdown textarea/preview; raw HTML выключен. |
| 134 | HubImage fallback вместо broken media. |
| 135 | Backend capabilities управляют edit/manage/moderation UI. |
| 136–137 | Remove/role change/archive confirmation с пользователем и последствиями; обычное сохранение без лишнего confirm. |
| 138 | Moderator override требует reason; metadata отражает override, тесты. |
| 139–140 | Deletion signals/service guard, member cascade, audit actor SET_NULL. Last manager account deletion → structured 409 даже с flags off. |
| 141 | Публичной смены username нет; admin rename limitation документирован, отдельная alias migration не вводилась. |
| 142–145 | Membership FK User, не nickname; нет owner; unique user/city row, несколько городов разрешены; generic policy engine не нужен. |
| 146 | Optional tags/taxonomy UI отложены. |
| 147–149 | Shareable SPA routes + document titles, API additive без v2. SSR/полный OG renderer не добавлялся, как допускает SPA scope. |
| 150–152 | README/docs/env обновлены; backend владеет map config/grammar, frontend получает canonical URL. |
| 153 | Map outage не участвует в API path; missing coords/map_id → no CTA, page остаётся работоспособной. |
| 154 | Archive скрыт от guest/catalog, доступен moderator, history/memberships сохранены. Account явно показывает «В архиве» без ссылки на недоступный город. |
| 155–158 | Русские role labels/positions, human-readable audit с before/after, timezone-aware timestamps и locale UI. |
| 159 | Leadership manager/representative + username, roster username, contacts sort_order — стабильная сортировка. |
| 160 | Publication minimum: name/slug/short_description; media/location необязательны. |
| 161–162 | Completeness gamification не добавлена; registration completeness отдельно от optional public profile. |
| 163–165 | Domain endpoints, без generic admin mutation/bulk import/internal moderation notes. |
| 166–170 | Recognizable memberships/city facts, progressive management/moderation, one DB source, audited elevation, modular MVP. |
| 171–173 | Django modular monolith/React/PostgreSQL/BlueMap, без новых services/event bus/ACL engine. |
| 174–177 | ADR, Mermaid domain diagram, RBAC, API map; OpenAPI source of truth. |
| 178–180 | Review blocks описаны в architecture; по последнему указанию пользователя всё в одном локальном изменении, без PR/push. Рефактор только необходимого account/shell/contract integration. |
| 181–182 | Security/onboarding/complete-profile/complete-registration routes остаются; нет молчаливого удаления старого API. |
| 183–184 | Demo personas и manual matrix в rollout; права проверены live/API, UI/browser и tests. |
| 185 | Backend DoD пройден: migrations/constraints/services/contracts/admin/audit/seed/tests/lint/security gates. |
| 186 | Frontend DoD пройден: pages/forms/states/Gravity/responsive/tests/build. |
| 187 | Связная profile → membership → city → map вертикаль, live/browser evidence. |
| 188 | Scenario A passed: guest catalog → leader profile → city → canonical map link. Реальный BlueMap format проверен отдельно в ADR. |
| 189 | Scenario B passed: resident self memberships ItmoCraft/Alpha/Житель; account cards используют этот response. |
| 190 | Scenario C passed live: representative PATCH → public content → actor audit/revision; исходный content восстановлен. |
| 191 | Scenario D passed live: manager promotes resident → profile representative relationship → audit; исходная роль восстановлена. |
| 192 | Scenario E passed live + regression: PLATFORM_ADMIN 422, resident edit 403, scoped IDOR 404, manager restriction 403/last manager 409. |
| 193 | Scenario F: explicit legacy-no-memberships regression проверяет login/self/empty memberships/profile edit и неизменность account status/старых полей; migration test проверяет upgrade. Live account/security работают. |
| 194 | Scenario G passed live: Beta без location; CityMapCard тестирует отсутствие CTA. |
| 195 | Scenario H passed live: draft → active → archived, guest 404/catalog hidden, moderator history preserved. |
| 196 | Repository checks выполнены; точные команды и результаты в testing. |
| 197 | Нет отключённых failing tests, auth bypass, role localStorage, secrets в diff, Bootstrap expansion или destructive migration; git diff --check проходит. |
| 198–199 | Неоднозначности решены через code/tests/conventions и ADR; вертикальные review blocks вместо фрагментарных model/serializer задач. |
| 200 | P0–P2 и MVP deeplink выполнены; advanced map/tasks не входят в обязательный milestone. |
| 201–203 | Person/Profile/Community/City/Map связаны; все 12 архитектурных принципов сохранены. |
| 204 | Discovery/proposal A–J выданы до foundation и сохранены в docs. |
| 205 | Итоговый implementation-report содержит domains/files/migrations/API/routes/permissions/flags/map/checks/limitations/QA/personas. |
| 206 | Следующая итерация только roadmap: requests/rollback/UUID/marker sync; ничего из неё не включено автоматически. |
| 207 | Локальная рабочая вертикаль доступна для maintainer review; push/deploy требуют отдельного разрешения пользователя. |

## Явные границы завершения

Завершён обязательный **локальный MVP**, включая foundation, read API, account/
profile, city UX, management, moderation/history и BlueMap deeplink. Production
rollout не выполнялся по прямому указанию пользователя. Flags вне demo default-off.
Не считаются выполненными и не обещаются: revision rollback, edit review engine,
arbitrary social-link collection (MVP использует VK),
join requests/tasks/elections/server sync/notifications/real-time markers/SSR.
Это варианты вне обязательного MVP, перечисленные в исходном ТЗ и ADR.

Особенности review: Cities admin read-only; emergency mutations через audited
services/API. Raw SQL/QuerySet.update и ручная деактивация user в emergency admin
не являются governance API — сначала передайте manager duties. Публичной
деактивации аккаунта, обходящей deletion guard, не добавлено.

Перед production: maintainer проверяет локальный результат, выбирает реальные
города/управляющих, затем отдельно разрешает push и rollout. Команды запуска,
credentials location и последовательность ручной проверки — [rollout](rollout.md).

UX revision from maintainer feedback supersedes initial MVP presentation: invitations
with consent, contextual editors/uploads, public visibility-filtered residents,
profile/menu and security separation. See [ux-revision.md](ux-revision.md) and
[implementation-report.md](implementation-report.md) for current behavior and tests.
