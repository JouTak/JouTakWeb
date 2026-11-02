# Validation

Run repository checks from the root:

```bash
uv run ruff check .
uv run bandit -r backend/accounts backend/bff backend/core backend/featureflags backend/observability backend/backend backend/profiles backend/communities backend/cities -x '*/tests/*,*/migrations/*' --skip B104,B105
PYTHONPATH=backend DJANGO_SETTINGS_MODULE=backend.settings.dev uv run python scripts/check_frontend_openapi_contracts.py
uv run --group test pytest backend -q
uv run python backend/manage.py makemigrations --check --dry-run --settings backend.settings.hub_demo
uv run python backend/manage.py check --settings backend.settings.hub_demo
npm --prefix frontend run check
npm --prefix frontend run test:e2e
npm --prefix frontend run check:audit
```

Tests use the real session-token authentication flow, bounded contracts and
role policies. Coverage includes private serialization, IDOR, unsafe URLs,
invalid coordinates, stale versions, moderator rollout, atomic audit/revisions,
archive, default-private legacy accounts, account deletion, bulk deletion,
community suspension and a bounded leadership query count. MigrationExecutor
reverses only new apps inside the test DB, creates old core.UserProfile data,
and reapplies migrations to verify preservation. No real DB is used.

## PostgreSQL concurrency

SQLite skips three tests because it cannot prove row-lock semantics. Run all city
tests against an isolated local PostgreSQL; pytest creates/drops `test_postgres`.
The following example uses an ephemeral container and a temporary settings file.
Choose a free container name/port; never point this at an existing database.

```bash
docker run --rm -d --name joutak-hub-test-postgres -e POSTGRES_HOST_AUTH_METHOD=trust -p 127.0.0.1:55432:5432 postgres:16-alpine
cat > /tmp/hub_pg_settings.py <<'PY'
from backend.settings import dev
globals().update({k: v for k, v in vars(dev).items() if k.isupper()})
DATABASES = {"default": {"ENGINE": "django.db.backends.postgresql", "NAME": "postgres", "USER": "postgres", "HOST": "127.0.0.1", "PORT": "55432", "OPTIONS": {"options": "-c statement_timeout=15000 -c lock_timeout=12000"}}}
PY
PYTHONPATH=/tmp:backend DJANGO_SETTINGS_MODULE=hub_pg_settings uv run --group test --with psycopg-binary==3.2.3 pytest backend/cities -q
docker stop joutak-hub-test-postgres
```

The optional binary driver is a temporary test dependency, not a new production
package. Two independent connections race manager demotions and account deletions;
exactly one operation succeeds and the other receives `CITY_LAST_MANAGER`.
Concurrent invitation acceptance succeeds once, creates one membership and
records one acceptance audit event.

## Browser evidence

Playwright reuses the repository framework. New tests cover guest navigation,
flag-off access, the canonical map link, horizontal overflow at 320/768/1440 px,
and axe checks on the new surface. All existing design-prototype tests also run.
The browser QA against the actual local backend additionally verified login,
account memberships, editor preview, saving and a corresponding history entry.

## Final local evidence (2026-09-21)

- Full backend: **239 passed**, 3 subtests passed; two SQLite row-lock tests
  skipped by backend capability and passed on PostgreSQL.
- After the final archived-membership presentation change: focused domain/account
  regression **36 passed**, 2 SQLite skips; contract check passed again.
- PostgreSQL city suite: **37 passed**, including both concurrency races and
  upgrade of an existing private UserProfile.
- `npm run check`: lint, Prettier, stylelint, **64 Vitest tests**, build passed.
- Playwright: **6 passed**. A concurrent run with the backend suite exhausted
  two 30-second browser test budgets. The complete rerun after that workload
  finished passed in 20.3 seconds; assertions and timeouts were not changed.
- Ruff, Bandit, 29-call OpenAPI contract check, Django system checks and
  `makemigrations --check --dry-run` passed.
- `check:audit` production policy and production `pip-audit` passed.
- Live HTTP smoke on 127.0.0.1:8011 logged in all four demo personas and verified
  guest profile/city/map links, resident denial, representative save + history,
  manager promotion + profile update, role escalation/IDOR/last-manager denial,
  account status compatibility, absent location and draft/publish/archive.
  Changed Alpha content and roles were restored; a QA city remains archived.
  Local non-secret receipt: `.local/live-smoke-results.json`.
- Browser on the live demo verified that cancelling the unsaved-changes dialog
  preserves typed text, and confirming departure leaves stored content unchanged.
  Unit coverage also exercises browser Back and beforeunload.
- Live account and city management were visually checked at 375 px, including
  absence of horizontal overflow. Archived memberships show their lifecycle
  label without an inaccessible city link. Viewport was restored afterwards.

The legacy-without-membership scenario is covered by migration, profile and
account suites; the four seeded personas intentionally have community membership.

## Dependency fixes

The baseline dependency checks exposed existing advisories. Targeted updates:
react-router-dom/react-router 7.18.4, fast-uri 3.1.8, Django 5.2.17,
cryptography 50.0.1 and sqlparse 0.6.0. fido2 resolves to 2.2.1 for compatibility
with cryptography. `uv.lock` and all generated requirements are regenerated.
No audit suppressions or policy changes were added. The npm gate covers
production dependencies according to the existing policy, not every development
dependency advisory.

Upstream evidence: [React Router advisory](https://github.com/remix-run/react-router/security/advisories/GHSA-qwww-vcr4-c8h2),
[fast-uri advisory](https://github.com/fastify/fast-uri/security/advisories/GHSA-5jgf-p345-68v8),
[Django security release](https://www.djangoproject.com/weblog/2026/aug/04/security-releases/),
[cryptography changelog](https://cryptography.io/en/latest/changelog/),
[sqlparse advisory](https://github.com/andialbrecht/sqlparse/security/advisories/GHSA-prg7-hcfm-mfcr).

The cryptography upgrade follows its 49/50 compatibility notes. This project
does not use the removed legacy key type aliases or raw ChaCha20 interface;
the full auth/MFA/session regression suite passes on Linux Python 3.12.
Intel macOS no longer has upstream cryptography wheels and may require a source
build; production remains Linux.

## UX revision evidence (same local change set)

- Full backend regression: **248 passed**, 2 SQLite skips, 15 subtests.
- PostgreSQL cities: **48 passed**, including three concurrent scenarios.
- After adding upload quota: focused invitation/media suite **10 passed**,
  14 subtests, including actual multipart upload and structured 429.
- `npm run check`: **80 tests**, lint/format/styles/build passed.
- Final Playwright rerun after mobile changes: **6 passed** (27.1s).
- OpenAPI: **38 frontend calls**; Ruff/Bandit/Django system and migration checks pass.
- Live browser: invitation send → pending (count unchanged) → recipient accepts
  → toast + city card → manager removal with confirmation → updated count/history.
  Demo membership restored, audit retained. PNG uploaded and decoded preview
  visible; profile draft discarded. BlueMap link import populated numeric X/Z.
- Security loads session details after local SQLite IMMEDIATE transaction tuning.
  Public-profile menu target and separate settings verified. Mobile 390 px
  has no horizontal overflow; map/contact actions precede long narrative.

Earlier evidence above describes the initial MVP. These results supersede its
old test counts and initial UX (URL images, direct resident additions, large form).
