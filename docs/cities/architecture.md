# Community Profile Hub

Status: local MVP implementation, 2026-09-21. No deployment or push.

## Discovery

Baseline: `2bbe87d`. Clean working tree on main. Read root/frontend/backend
AGENTS, README, architecture/frontend conventions, App/routes/components,
accounts/core/BFF/featureflags/observability and the OpenAPI checker.

* React 18/Vite/Router 7, Gravity UI; Bootstrap is legacy. Domain clients
  use sessionClient. PageDocument BFF is for landing pages; bootstrap can
  expose flags independently. Vitest/RTL and Playwright already exist.
* Django 5.2/Ninja/allauth, default Django User, email signup. No public
  username mutation endpoint. Usernames remain editable by emergency admin;
  an admin rename changes public URLs (no alias engine in this release).
* `core.UserProfile` stores Minecraft/VK/ITMO and completion/origin. Keep
  its table and account services unchanged. Avatar upload helper exists but
  default User has no avatar field: the endpoint currently cannot persist it.
* Feature registry supports boolean flags, staff, groups, allowlists and
  percentages. Reuse it, default all new surfaces off. Flags are rollout
  gates, never authorization grants.
* simple-history exists for flags; no shared product audit. City revisions
  need one atomic snapshot including contacts, so a custom CityRevision is
  smaller than reconstructing several independent historical tables.
* No existing community/membership domain. GitHub open PR search for
  profile/RBAC/flags and open issue search for profiles/community/cities/RBAC
  returned no matches. Related prior work: PRs 96, 104, 105.

## Context boundaries

`accounts`: authentication, security, private personalization, deletion.
`profiles`: opt-in public representation and serialization/visibility policy.
`communities`: generic community and scoped membership.
`cities`: city facts, contacts, governance, policies, mutation services,
read queries, audit/revisions and moderation API. No generic moderation app
until a second domain needs it. `core` gains no social models.

Frontend pages stay in pages/{account,profile,communities,cities,moderation};
components and domain API clients mirror those responsibilities. Small
shared hub primitives use Gravity UI and existing theme tokens. Markdown
is narrative only, with raw HTML disabled; URLs receive independent checks.

## Routes / API

| UI | API |
| --- | --- |
| /account, /account/profile | GET/PATCH /api/profiles/me |
| /account/communities | GET /api/account/memberships |
| /u/:username | GET /api/profiles/public/{username} |
| /communities, /communities/:slug | GET /api/communities, /{slug} |
| /cities | GET /api/cities?q=&recruitment=&page= |
| /cities/:slug | GET /api/cities/{slug}; GET/PATCH /{slug}/membership |
| /cities/:slug (contextual editors) | PATCH /api/cities/{slug}; GET /{slug}/members; PATCH/DELETE /{slug}/members/{membership_id} |
| /cities/:slug?tab=residents | GET /api/cities/{slug}/residents; GET/POST /{slug}/invitations; DELETE /{slug}/invitations/{id} |
| /cities/:slug?tab=history | GET /api/cities/{slug}/history (lazy) |
| /account invitations | GET /api/account/city-invitations; POST /api/account/city-invitations/{id} |
| Image pickers | POST /api/profiles/images; POST /api/cities/{slug}/images (multipart file) |
| Map link import | POST /api/cities/{slug}/map-location (validated URL → location) |
| /moderation/cities | GET/POST /api/moderation/cities; PATCH /api/cities/{slug} for lifecycle |

OpenAPI is authoritative for the implemented request/response shapes.
Unknown request fields are rejected. Detail reads never reveal unpublished
existence to unauthorized viewers. Personal responses are private/no-store.
Moderation supports status/search and `recent_days` (1–365) filters and shows
community visibility, current managers and the latest actor.

The root uses a React Router data router with the existing App route tree.
This provides supported `useBlocker` handling for dirty city/profile forms;
beforeunload also protects reload/tab close. Providers and legacy URLs remain.

## Review blocks in one local PR

1. Additive domain/schema/admin/seed foundation and invariants.
2. Central policy, visibility, read API, typed contracts.
3. Account/profile/community UI and legacy compatibility.
4. City catalog/detail, map and privacy-aware leadership.
5. Atomic management, roster/roles, revision history and confirmations.
6. Moderator creation/archive/history, local demo and end-to-end validation.

## Risks and assumptions

Opt-in publication avoids disclosing legacy identities. Display name defaults
to username, never private first/last name. Community visibility means shared
ACTIVE community membership, not merely being authenticated. Contacts use
the same scope. City membership visibility defaults to community.

One role per membership is sufficient now. Community roles do not confer
platform moderation. Multiple cities per user are allowed. Manager assignment
is platform-only; positions are presentation. Active cities require a short
description. Contacts and external links share one ordered typed entity.

Audit actor is nullable; no email/ISU/IP or username snapshot is retained on
account deletion. Revisions contain city content only. User deletion locks
the user and managed cities and blocks the last manager until responsibility transfers.
Archived cities retain governance/history. Last-manager guarantees require
PostgreSQL row locks; SQLite remains a sequential development/test backend.
Optimistic version checks reject stale content edits rather than overwriting.

## Threat review

Stored XSS: Markdown renders without HTML; unsafe links/images rejected.
IDOR: membership lookup always includes city. Escalation: bounded city roles,
central policies and explicit platform permission. CSRF: new mutations use
existing X-Session-Token auth, not ambient cookie-only authorization.
Enumeration: uniform 404 for hidden city/profile. Audit is restricted to
editors/moderators, not public city data. SSRF: no server fetch of media URLs.
Revoked sessions must fail before management. Account deletion and role
mutations share city locks; all successful sensitive changes audit atomically.

Non-goals: tasks, elections, economy, server permissions/sync, notifications,
generic ACL/workflow, polygon editing, realtime markers, rollback.


Hub APIs require the moderation flag for moderator actors using management
operations, including manager demotion/removal. This keeps moderator powers
behind the same rollout gate as the console. Capability serialization agrees.

City admin screens are deliberately read-only: emergency inspection is safe,
while mutations use audited services/UI. Community memberships use existing
simple-history and Django admin. Direct ORM bulk updates are an operator
escape hatch and must not be used for governance; services enforce invariants.
User/CommunityMembership deletion signals also protect normal ORM/admin deletes
and multi-user deletion. Deactivating users with raw ORM/admin edits requires
transferring their manager duties first; no replacement auth identity is added.

A discovered pre-existing admin WebAuthn bug assigned to `allauth.context.request`
and permanently shadowed its ContextVar. This change uses `request_context` and
adds regression coverage because the full suite exposed subsequent login failures.

Public profile reads use `/api/profiles/public/{username}` so a legacy user
named `me` cannot collide with the authenticated `/api/profiles/me` endpoint.
Browser URLs remain `/u/:username`.

## Player connections

The later explicit request for player discovery/subscriptions extends the initial
MVP scope inside `profiles`, behind `community_profiles_ui`. `/players` searches
visible profiles and offers a personal following filter. Profile cards reuse the
visual direction of reference PR #36. No follower list enters the global BFF.

| Surface | Additional typed API |
| --- | --- |
| /players | GET /api/profiles/players?q=&page=1&following=false |
| Profile communication circle | GET /api/profiles/public/{username}/connections?direction=following&page=1 |
| Follow / unfollow | POST / DELETE /api/profiles/public/{username}/follow |
| Own contact editor | GET / PATCH /api/profiles/me/contacts |

Visibility is applied in SQL before search/count/pagination. Public profiles
serialize each contact through the visibility policy; following never expands
access. Private connections are the migration default. See the full
[design and privacy decisions](player-connections.md).

## UX revision

[Accepted review](ux-revision.md) separates interest communities from city navigation,
puts residents and lazy history on the city page, and replaces the giant form with
contextual editors. `/cities/:slug/manage` redirects to its in-page editor. Direct
POST `/cities/{slug}/members` is retained as a structured 409
`CITY_INVITATION_REQUIRED`; it cannot bypass recipient consent. Initial moderator
manager assignment is the explicit bootstrap exception. Invitations never grant
roles before acceptance, and acceptance always starts as resident.

Uploaded PNG/JPEG/WebP is bounded, decoded, resized/re-encoded without metadata,
and stored using existing Django media storage with random filenames. URLs use
`/media/hub/<32 hex>.webp`; images are public assets, independent of profile
visibility. Quota `RATELIMIT_HUB_IMAGES` defaults to 20/h per account.
