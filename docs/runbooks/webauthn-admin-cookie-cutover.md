# WebAuthn And Admin Cookie Cutover

This runbook covers the production cutover and WebAuthn credential
re-enrollment procedure for issue #173. Changing an RP ID and changing cookie
scope have different rollback constraints, but the fixed adapter, exact-origin
policy, host-only cookies and ingress routes must become active atomically.

## Security Contract

Production must keep these invariants after the first rollout:

- browser API and BFF requests use `https://joutak.ru/api` and
  `https://joutak.ru/bff`;
- `joutak.ru` and the temporary `api.joutak.ru` alias are API hosts, while
  `admin.joutak.ru` is the only admin host;
- the Django session cookie is `__Host-joutak_session`, `Secure`, `HttpOnly`,
  `SameSite=Lax`, `Path=/`, and has no `Domain` attribute;
- the CSRF cookie remains named `csrftoken` for the existing frontend
  contract, but is `Secure`, `SameSite=Lax`, `Path=/`, and host-only;
- no auth or CSRF cookie uses `Domain=.joutak.ru`;
- credentialed CORS is limited to the required `/api` and `/bff` routes and
  never decorates admin responses;
- `DJANGO_CSRF_TRUSTED_ORIGINS` contains only the public origin required by
  the legacy API transport; it never contains `admin.joutak.ru` or a wildcard
  covering that privileged origin, because same-origin admin requests need no
  CSRF trust exception;
- every unsafe `/admin` method requires the exact configured admin `Origin`,
  or an exact-origin `Referer` fallback when `Origin` is absent; the public
  sibling, opaque `null`, malformed, missing and unexpected-port contexts fail
  closed before Django CSRF processing and never receive CORS headers;
- the default/allauth, project rate-limit and WebAuthn replay state use three
  distinct DatabaseCache tables with `CACHE_MAX_ENTRIES=100000`; their
  fail-closed backend removes expired rows but never culls live security
  state. Capacity exhaustion rejects new security keys instead of resetting
  a counter, epoch or replay claim;
- the interim issue #173 host policy exposes only admin, code-owned static and
  media paths on `admin.joutak.ru`; API, BFF and account routes stay denied;
- the canonical WebAuthn RP ID remains `joutak.ru` after credentials have
  been issued with it.

`__Host-` is part of the session-cookie security boundary. Browsers only
accept such a cookie when it is Secure, has `Path=/`, and omits `Domain`.
Do not work around a rejected cookie by removing the prefix.

## Ingress Topology

The Swarm manifest routes requests as follows:

| Public request                 | Upstream       | Expected result                    |
| ------------------------------ | -------------- | ---------------------------------- |
| `joutak.ru/api[/...]`          | backend        | Django API                         |
| `joutak.ru/bff[/...]`          | backend        | Django BFF                         |
| `joutak.ru/accounts[/...]`     | backend        | allauth/OAuth routes               |
| `joutak.ru/media[/...]`        | backend        | media route (see caveat below)     |
| `joutak.ru/health[/]`          | backend        | health response                    |
| `joutak.ru/admin[/...]`        | backend policy | explicit denial, never SPA HTML    |
| `joutak.ru/static/admin[/...]` | backend policy | explicit denial                    |
| other `joutak.ru/*`            | frontend       | React application                  |
| `api.joutak.ru/*`              | backend        | temporary compatibility API        |
| `admin.joutak.ru/*`            | backend policy | only admin, static and media paths |

Traefik forwards the original `Host`; there is no `StripPrefix`. The backend
router has a higher explicit priority than the frontend catch-all.

The checked-in Traefik image is v3.1 and therefore uses the Swarm provider,
not the removed Docker `swarmMode` option. The service must run on a manager
node so its Docker socket can enumerate Swarm services.

The manifest defines a self-contained ACME HTTP-challenge resolver named `le`.
Set `TRAEFIK_ACME_EMAIL` to a real monitored operator address before deploy;
the checked-in environment template deliberately leaves it empty so Compose
fails closed until it is supplied. ACME state is stored in the `letsencrypt`
volume. The repository also defines the
`redirect-to-https` dynamic middleware used by its HTTP routers.

Supply `TRAEFIK_ACME_EMAIL` in the environment of the Compose/stack command
or its deployment automation. The backend's `.env.production` file does not
configure the separate Traefik service.

## Media Is A Separate Deployment Decision

The Traefik rule sends `joutak.ru/media[/...]` to the backend so it cannot fall
through to React's `index.html`. That fulfills the routing contract, but not
the file-serving contract. In production, `backend.urls` only adds Django's
`static(..., MEDIA_ROOT)` route when `DEBUG=True`; the Gunicorn service will
therefore return 404 for media unless the actual deployment supplies a media
upstream. Never enable `DEBUG` or Django development static serving to fix it.

The preferred production design is a dedicated, unprivileged media
origin/service with no auth cookies, read-only storage, directory listing
disabled, correct image MIME types and `X-Content-Type-Options: nosniff`.
If the existing external nginx already owns `joutak.ru/media`, keep that
explicit rule until the dedicated origin is available. Otherwise treat file
serving as a deployment follow-up while preserving the checked-in route to the
backend. In either case:

1. version or identify the real media routing source of truth;
2. verify a known safe image through the public media URL;
3. verify the admin media behavior matches the interim #173 host policy and
   does not accidentally expose any API/account route;
4. schedule the stricter cookieless media-origin isolation from parent issue
   #172 before adding new user-controlled media types.

## Preflight

1. Record the application image digests and current stack revision.
2. Audit DNS for every known `*.joutak.ru` name. Resolve dangling CNAMEs,
   forgotten preview deployments and any host that can serve user-controlled
   HTML before rollout. Never add staging or preview hosts to the production
   WebAuthn origin allowlist; use an isolated staging RP/domain instead.
3. Confirm the active ingress source of truth. If an external nginx is still
   in front of Traefik, compare its `/api`, `/bff`, `/accounts`, `/health`,
   `/admin` and `/media` rules with the table above.
4. Set `TRAEFIK_ACME_EMAIL` to a monitored operator address, confirm the `le`
   resolver loads, and verify that the HTTPS routers have valid certificates.
5. Inspect response cookies on both public and admin hosts without publishing
   their values. Record only name, Domain, Path, Secure, HttpOnly and SameSite.
6. Count live Django/allauth/project session records. Do not print session
   keys, refresh JTIs, tokens or cookie values.
7. Confirm `joutak_cache_table`, `joutak_ratelimit_cache_table` and
   `joutak_webauthn_replay_cache_table` exist. The no-argument
   `createcachetable` entrypoint creates all configured DatabaseCache aliases.
   Alert on each table's unexpired row count well before 70% of
   `CACHE_MAX_ENTRIES`. At capacity, new authentication/rate/replay state
   fails closed and can cause 400/429/500 responses; never clear a live table
   as an availability workaround, because that would reset security state.
   Increase capacity or restore the backend, retain existing rows, and verify
   expired-row cleanup before reopening authentication traffic.
8. Build a release-candidate image containing the fixed WebAuthn adapter,
   exact-origin policy, host-only cookie settings, both audit/invalidation
   commands and ingress configuration. Do not switch application traffic yet.
9. Deploy that exact release candidate and routing policy to isolated staging,
   then complete the pre-production browser evidence matrix below. Do not
   proceed on an untested image or configuration.
10. Confirm at least two staff users have tested TOTP and have usable saved
    recovery codes before invalidating sessions. Select one or two of them as
    the canary cohort and confirm the remaining staff can use a non-Passkey
    fallback if the canary fails.
11. Prepare a temporary cutover response rule at the ingress/deployment layer
    that _appends_ the legacy Domain-cookie expiry headers described below.
    There is no permanent application middleware for this cleanup in the
    repository. Do not use a response-header feature that replaces Django's
    other `Set-Cookie` headers.
12. Run the deploy gate and the targeted infrastructure tests:

```bash
bash scripts/check_deploy_gate.sh
uv run pytest backend/backend/tests/test_smoke_infra.py -q
```

## Pre-production Browser Evidence

Record a pass/fail result and browser version for each row on isolated staging
before production rollout. Run the platform-passkey scenario in every listed
browser. Also run at least one external authenticator/security-key scenario on
a browser and device combination that supports the available hardware.

| Browser                         | Required platform-passkey flows                                           |
| ------------------------------- | ------------------------------------------------------------------------- |
| Chrome or Chromium              | public registration/login, MFA reauthentication, admin password + Passkey |
| Firefox                         | public registration/login, MFA reauthentication, admin password + Passkey |
| Safari                          | public registration/login, MFA reauthentication, admin password + Passkey |
| Yandex Browser used by the team | public registration/login, MFA reauthentication, admin password + Passkey |

For the external authenticator/security-key scenario, repeat public
registration/login and admin password plus Passkey. In every browser also
verify password login, password plus TOTP, one recovery-code login and Passkey
add/rename/delete. Record only browser/version, authenticator category and
pass/fail status; never retain credential IDs, challenges, codes, session
tokens or raw WebAuthn payloads.

## WebAuthn RP Audit And Re-enrollment

Before switching traffic, run the read-only audit from the release-candidate
image against the production database. Supply the canonical production
WebAuthn environment to that one-off container because production settings
require it, but do not route user traffic to the container:

```bash
python backend/manage.py audit_webauthn_rp_ids \
  --candidates joutak.ru,api.joutak.ru,admin.joutak.ru
```

The command classifies credentials from their stored authenticator data and
prints aggregate counts without changing them. `unknown` or `unparseable`
greater than zero is a hard stop: investigate those credentials before the
cutover. Do not guess their RP ID and do not silently exclude them. Retain the
aggregate output as rollout evidence without recording credential payloads.

An RP ID is cryptographically bound into a WebAuthn credential. Never rewrite
an existing credential row to make a legacy credential appear canonical. The
re-enrollment sequence is:

1. verify TOTP and saved recovery-code readiness for staff, then identify one
   or two staff canaries;
2. perform the atomic deployment sequence below;
3. have each canary sign in through a tested fallback and register a new
   Passkey on `https://joutak.ru` with RP ID `joutak.ru`;
4. require each canary to complete a fresh public Passkey authentication and
   a fresh direct `https://admin.joutak.ru` Passkey authentication;
5. after the canaries pass, open re-enrollment to the remaining users while
   retaining their legacy credential records for a grace period of at least
   seven days;
6. delete a user's legacy credential only after that user has registered and
   successfully reauthenticated with a canonical credential and the grace
   period has elapsed. Never bulk-delete or rewrite legacy credentials based
   only on the audit classification.

The retention grace period preserves evidence and a per-user recovery record;
it does not make a legacy credential compatible with the canonical RP ID.
Affected users need a tested non-Passkey fallback to re-enroll.

## Legacy Cookie And Session Invalidation

Changing only `SESSION_COOKIE_DOMAIN` is unsafe. A browser can send the old
domain cookie and the new host-only cookie together. The new session name
prevents ambiguous parsing, but the legacy session remains bearer material
until both browser and server state are invalidated.

The cutover must perform all of the following in one maintenance window:

1. stop accepting `sessionid` and start accepting only
   `__Host-joutak_session`;
2. revoke the corresponding server-side Django sessions, allauth user
   sessions, project `UserSessionMeta` records and refresh-token mappings;
3. blacklist/revoke mapped refresh JWTs according to the project's session
   service instead of only deleting `django_session` rows;
4. return an expiry cookie for the legacy scope on public, API and admin
   responses:

   ```text
   sessionid=; Domain=.joutak.ru; Path=/; Max-Age=0; Expires=<past>; Secure; HttpOnly; SameSite=Lax
   ```

5. defensively expire `csrftoken` with `Domain=.joutak.ru` if production ever
   emitted that scope, while continuing to issue the new host-only
   `csrftoken`:

   ```text
   csrftoken=; Domain=.joutak.ru; Path=/; Max-Age=0; Expires=<past>; Secure; SameSite=Lax
   ```

6. defensively expire `joutak_refresh` with `Domain=.joutak.ru` and
   `Path=/api/auth/refresh` if production ever emitted that scope:

   ```text
   joutak_refresh=; Domain=.joutak.ru; Path=/api/auth/refresh; Max-Age=0; Expires=<past>; Secure; HttpOnly; SameSite=Lax
   ```

7. never attach `Domain` to the new session, refresh or CSRF cookie, including
   on deletion responses for the new names.

Deleting only Django `Session` rows is insufficient in this repository:
refresh validates `UserSessionMeta` and `UserSessionToken` mappings. Preview
and execute the project's aggregate-only, idempotent cutover command:

```bash
python backend/manage.py invalidate_legacy_auth_sessions
python backend/manage.py invalidate_legacy_auth_sessions --apply
```

The dry run and applied output must contain counts only. If this command is not
present and tested in the release candidate, stop the rollout rather than
using an ad-hoc production shell command.

Browser expiry and server revocation are separate checks. The expiry headers
must be enabled temporarily at the ingress/deployment layer during this
cutover because the repository has no permanent cleanup middleware. Send them
from every affected public, API and admin host for at least the cutover window,
then remove the temporary rule only after verification with a browser profile
that held the old cookies. Verify both browser expiry and server revocation.

## Deployment Sequence

1. Keep current application traffic on the old release. Run
   `audit_webauthn_rp_ids` from the release-candidate image, with the canonical
   production WebAuthn environment, and stop if any credential is unknown or
   unparseable.
2. Confirm the selected one or two staff canaries can use TOTP and saved
   recovery codes. Confirm the temporary browser-expiry mechanism is ready to
   append, rather than replace, `Set-Cookie` headers at cutover.
3. Run `invalidate_legacy_auth_sessions` without `--apply` and review its
   aggregate dry-run counts. Do not expose session keys, JTIs or tokens.
4. Enter maintenance mode and drain authentication/session writes. Run
   `invalidate_legacy_auth_sessions --apply` while writes remain drained. The
   command atomically clears Django/allauth sessions, revokes project session
   mappings and blacklists outstanding refresh tokens; it is safe to rerun.
5. While writes remain drained, atomically switch traffic to the release that
   enables all of the following together: fixed canonical-RP adapter,
   `WEBAUTHN_RP_ID=joutak.ru`, exact signed-origin policy, host-only
   `__Host-joutak_session`, host-only refresh/CSRF cookies, same-origin ingress
   routes and temporary legacy Domain-cookie expiry headers. There is no safe
   intermediate deployment with the new production settings but the old RP
   behavior.
6. Verify backend paths do not return `index.html`, verify the cookie matrix,
   and confirm old sessions and refresh tokens are rejected. Reopen auth writes
   only after these checks pass. Expect every user and administrator to sign
   in again.
7. Have the one or two staff canaries register a new canonical Passkey through
   `https://joutak.ru`, then verify fresh public and direct-admin Passkey
   authentication before opening re-enrollment broadly.
8. Maintain the legacy-credential grace period for at least seven days and
   follow the per-user deletion conditions above. Remove temporary browser
   expiry headers only after the legacy-cookie verification window is complete.

## Verification Matrix

Run these checks with a clean browser profile and again with a profile that
contains the old `.joutak.ru` cookie.

| Check                                                  | Expected                                   |
| ------------------------------------------------------ | ------------------------------------------ |
| `joutak.ru/api/...`                                    | backend JSON, not SPA HTML                 |
| `joutak.ru/bff/...`                                    | backend JSON, not SPA HTML                 |
| `joutak.ru/media/...`                                  | backend/media upstream, never SPA HTML     |
| `joutak.ru/health/`                                    | `200` health response                      |
| `joutak.ru/admin/`                                     | explicit `403`, not frontend `200`         |
| `api.joutak.ru/admin/`                                 | `403`                                      |
| `admin.joutak.ru/`                                     | redirect to `/admin/`                      |
| `admin.joutak.ru/api/...`                              | `403` and no ACAO/ACAC                     |
| `admin.joutak.ru/media/...`                            | only the documented interim media behavior |
| public session `Set-Cookie`                            | new name, no Domain                        |
| admin session `Set-Cookie`                             | new name, no Domain                        |
| admin unsafe request with exact admin `Origin`         | reaches Django CSRF/view policy            |
| admin unsafe request with public/null/missing `Origin` | `403` and no ACAO/ACAC                     |
| public cookie jar on admin request                     | public session absent                      |
| admin cookie jar on public/API request                 | admin session absent                       |
| legacy `sessionid; Domain=.joutak.ru`                  | expired and rejected                       |

Also verify password login, public Passkey login, admin password plus Passkey,
admin password plus TOTP and one recovery-code flow. Do not record credential
payloads, codes, session identifiers or raw `Set-Cookie` values.

## Rollback

- Do not restore the old `Domain=.joutak.ru` cookie or old server sessions.
- Do not return the WebAuthn RP ID to a host-derived value after issuing a
  `joutak.ru` credential.
- If the same-origin router fails, restore the previous ingress rule while
  keeping the host-only cookie and fixed RP policy. Public auth can temporarily
  use the legacy API transport only if its exact-origin flow remains valid.
- If Passkey completion fails, disable the affected Passkey UI/flow and use
  tested TOTP/recovery fallback; do not weaken signed-origin verification.
- If the media upstream is unavailable, preserve the `/media` route away from
  the SPA and restore only the previous media-serving upstream.

After rollback, rerun the routing and cookie verification matrix and check for
unexpected 401/403/500, WebAuthn origin rejection spikes and administrator
lockout.
