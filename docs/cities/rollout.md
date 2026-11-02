# Local review and rollout

All work remains local until maintainer review and explicit push permission.
Do not run seed or migrations against production while validating this PR.

1. Additive migrations; test both empty database and upgrade from existing
   core.UserProfile records. No required new registration fields.
2. Backend and frontend merge behind default-off boolean flags:
   `community_profiles_ui`, `communities_ui`, `cities_ui`,
   `cities_management_ui`, `cities_moderation_ui`, `cities_map_integration`.
3. `sync_feature_registry`, then `seed_itmocraft_community` (idempotent).
4. Enable staff rules, then a selected FeatureGroup/allowlist, then everyone.
   Use page-independent rules so shell and API make the same rollout decision.
   Management requires cities_ui; moderator requires both plus moderation UI.
5. Create real cities in moderator UI. No demo data in production.
6. Disable flags to roll back UI/API exposure; keep additive tables/history.

Local demo commands are below; exact checks are in [testing.md](testing.md).
Demo identities are isolated development records with a caller-supplied
password; no production usernames/IDs and no committed credentials.

## Manual acceptance

Guest: cities → city → leader profile → city → map. No management controls.
Resident: account → communities/city with Житель; editing forbidden.
Representative: content/contact edit, preview, save, history; no roster rights.
Manager: invite community member, wait for acceptance, assign representative,
remove with confirmation;
attempt manager escalation and last-manager removal must fail.
Moderator: create with initial manager, drafts/archive filters, inspect history.
Legacy user: security/onboarding/profile continue working; empty memberships.
Missing location: usable city page without map CTA. Hidden profile: no email,
ISU or private identity leaked through city leadership or profile response.
Two editors: stale version yields conflict, preserving unsaved form input.

History is required in MVP; rollback is deliberately deferred until a separate
review covers restoring contacts/location without restoring obsolete powers.

## Run the isolated local demo

### Containers (recommended for keeping the review running)

The dedicated Compose file builds the existing backend/frontend Dockerfiles and
bind-mounts the same `.local/community-hub.sqlite3` demo database. It publishes
only loopback ports and uses `restart: unless-stopped`; Docker restarts the
services after a daemon/host restart unless they were explicitly stopped.
Docker Compose and Buildx are required. It does not start the older PR stack or
use its PostgreSQL volumes.

```bash
mkdir -p .local
chmod 700 .local
HUB_DEMO_UID=$(id -u) HUB_DEMO_GID=$(id -g) docker compose -f compose.hub-demo.yaml up -d --build --wait
docker compose -f compose.hub-demo.yaml ps
docker compose -f compose.hub-demo.yaml logs --tail=100
```

Open http://127.0.0.1:5174/cities; API is http://127.0.0.1:8011.
On a fresh checkout, seed once after the containers start:

```bash
docker compose -f compose.hub-demo.yaml exec backend python manage.py seed_hub_demo --enable-hub
```

For an existing review DB, seeding again is unnecessary. The backend applies
additive migrations at startup; images rebuild only with `--build`. To resume
already-built containers without rebuilding:

```bash
docker compose -f compose.hub-demo.yaml up -d --wait
```

To stop them explicitly: `docker compose -f compose.hub-demo.yaml stop`.
Do not run the host processes below on the same ports at the same time.

### Host processes (alternative)

From the repository root (two terminals). This uses `.local/community-hub.sqlite3`
(ignored by git), never `backend/db.sqlite3` or production PostgreSQL. Emails
stay in memory. The seed refuses any other database/settings combination.

```bash
uv run python backend/manage.py migrate --settings backend.settings.hub_demo
uv run python backend/manage.py seed_hub_demo --enable-hub --settings backend.settings.hub_demo
uv run python backend/manage.py runserver 127.0.0.1:8011 --noreload --settings backend.settings.hub_demo
```

```bash
VITE_BACKEND_URL=http://127.0.0.1:8011 npm --prefix frontend run dev -- --host 127.0.0.1 --port 5174
```

Open http://127.0.0.1:5174/cities. Seed prints a generated password only for newly
created users; optionally supply `HUB_DEMO_PASSWORD` in the process environment.
Repeating it preserves passwords, city content and existing profile/privacy choices.
The current review workspace stores access details in `.local/demo-access.txt`.
Do not commit this file. Login accepts the usernames below or their
`<username>@example.local` emails. Use separate browser sessions for personas.

| Persona | Username | Expected experience |
| --- | --- | --- |
| Guest | no login | Catalog, city, public leader profiles, BlueMap |
| Resident | hub_resident | Alpha membership, no editing |
| Representative | hub_representative | Alpha content/contacts editing and history |
| Manager | hub_manager | Alpha/Beta, roster, representative assignment |
| Moderator | hub_moderator | Create/archive, manager assignment, all histories |

`city-alpha` has sample coordinates; `city-beta` deliberately has none.
These cities and coordinates are fictional demo data, not claims about the
actual Minecraft world. Demo users opt into public profiles/memberships.
Legacy/real accounts default to private profiles and community-only memberships.
The moderator has `cities.moderate_city`, not superuser powers. Django Admin
MFA/host restrictions remain unchanged.

## Review script

1. Guest: `/cities` → Alpha → manager profile → Alpha → BlueMap. Verify the URL
   contains `#joutak:1240:0:-438:1500:0:0:0:1:flat`. Beta must have no map CTA.
2. Login resident → `/account`: ItmoCraft, Alpha, “Житель”. Try Alpha management:
   no editor. `/account/security`, `/account/profile` and onboarding aliases work.
3. Login representative → Alpha → edit description/contact → preview → save.
   Reopen the public page; management history must contain the new revision.
4. Login manager → change resident to representative, confirm, check profile
   relationship and history. Restore resident afterwards to keep demo personas.
   Manager cannot assign/edit/remove managers; API rejects forged role input.
5. Login moderator → `/moderation/cities` → create a draft with `hub_manager`.
   Publish it, archive it, verify guest 404 and moderator history retained.
6. Open two editors: first saves; second receives a version conflict and keeps
   its draft. Reload explicitly after copying any wanted unsaved changes.
7. `/account/profile`: make profile private. A separate guest session cannot
   open it; leadership degrades gracefully. ISU/email never occur in public API.
8. Set membership visibility to “Только я” on the city residents tab: public relationship
   disappears; managing the roster does not republish it.
9. Test critical forged API requests via automated suite: cross-city ID,
   PLATFORM_ADMIN role, unsafe contact URL, last-manager removal/deletion.

Content edits publish immediately **for active cities**. Draft-city edits remain
unpublished until a moderator publishes. No reviewer workflow is implied by Save.
Lifecycle and publication controls are moderator-only.

## Production preparation (not performed)

Back up DB; apply additive migrations; sync registry; seed only ItmoCraft; enable
staff/group rollout. Rerun dependency audits against the release lockfiles. Publish
real cities with explicit manager and profile consent. Do not run demo seed or
use `hub_demo` settings in production. Feature flags can disable exposure without
dropping data; reversing migrations would delete new-domain data, so use flags
for operational rollback.

## UX revision smoke

1. Manager account menu → Profile opens `/u/hub_manager`; settings are a separate
   action. Account communities lists interest communities only; archived QA cities
   are absent from current city cards.
2. City → edit a single section, preview, save. Dirty close → cancel keeps input.
   Image picker accepts PNG/JPEG/WebP ≤3 MiB; invalid content is rejected.
3. City residents → invite `hub_resident` to Beta. Before acceptance the member
   count stays unchanged. Login recipient → account → accept → toast and city card.
   Decline/revoke/expired invitations grant no membership.
4. Paste a BlueMap link in location editor; imported X/Z appear, camera Y is not
   treated as Minecraft altitude. Save remains explicit. Beta can stay without
   location. Contacts allow only Discord invite, Telegram and VK.
5. History is requested only after opening its tab. Ordinary views show neither
   version numbers nor raw content snapshots. Security shows grouped login options
   without personalization cards or duplicate account navigation.

Local media persists in `.local/media` across demo rebuilds. Production must
serve the existing MEDIA_ROOT route and back it up. Uploads are public by URL;
unreferenced files after cancelled editing are retained, with deletion/retention
policy deferred. They have random names and a per-account upload quota. SQLite
demo uses IMMEDIATE transactions and a 20-second busy timeout for concurrent
session touches; PostgreSQL remains the production concurrency target.

## Player discovery smoke

Apply additive `profiles/0003` before deploying the new UI. It adds subscriptions,
contacts and private-by-default circle visibility without publishing legacy users.
Existing `community_profiles_ui` gates the directory and all social endpoints.
`RATELIMIT_PROFILE_SOCIAL` defaults to 60 mutations per account per hour.

1. Guest: `/players` → search `resident` → `hub_resident`. Only public identities
   are visible; contacts and circle require their own audience settings. Guest
   cards link through avatar/name without a separate CTA; neither cards nor profiles prompt guests to
   log in and follow. Follow actions appear only for authenticated viewers.
2. Manager: follow resident → `/players?view=following` → resident card. Unfollow
   removes the relationship and refreshes the filtered list. Repeated requests
   do not duplicate the relationship.
3. Own profile → settings → contacts: add a fictitious Discord username for local
   QA. New contact defaults to private. Select audience explicitly; inspect the
   profile using an independent guest session. Restore demo contacts afterwards.
4. Profile privacy → “Мои подписки и подписчики”: public/community/private.
   Incoming lists additionally hide people whose own connections remain private.
   Making a profile private hides it from search and other people's lists.
5. Link icon on a profile copies its canonical browser URL and shows a short toast.
   Clipboard refusal gives a short error without printing a long URL in the hero.
6. Verify mobile directory and profile, then restore sample subscriptions/contacts.
   Existing demo personas and city memberships stay unchanged.

## Profile cards and mutual subscriptions

Apply additive `profiles/0004` before loading the new backend image. It sets the
approved 2026-01-01 baseline on existing profiles, preserves all old fields and
uses that default for new profiles. It does not change account activation,
profile visibility or existing subscription rows. Reversing removes only the
new column. The dependency lock and all generated requirements now include
pymorphy3 and its Russian dictionary.

1. Open `/u/hub_manager`: name below nickname; player days then first server date
   (compact “с 01.01.2026”). No tabs and no waiting-for-server notice.
2. Make both demo profiles' connections public through their privacy settings
   for this smoke only. Resident follows manager: manager has a subscriber.
   Manager follows resident back: subscriber moves into the friends avatar grid.
   The matching counters refresh without reloading the whole profile.
3. Open an avatar to navigate to that player. Remove one follow: mutual friendship
   disappears and the remaining directed subscription stays intact.
4. Restrict one player's connections: another viewer sees neither their identity
   nor a count leak. Hidden cards must not show a misleading zero.
5. Check 320/768/1440 widths, keyboard focus/tooltips, empty lists and request retry.
   Restore demo visibility and test subscriptions after QA.


Minecraft identity smoke: set different username, Minecraft nickname and display
name on a demo persona. City administration/residents, player cards and avatar
labels should show the nickname; links should still target `/u/{username}`.
The real name should appear only on the profile. Hide Minecraft data and check
that lists use the username rather than disclosing the hidden nickname. A city
manager must respect those same limits in the residents and invitations lists.
