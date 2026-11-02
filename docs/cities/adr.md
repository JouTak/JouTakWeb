# ADR: community identity and city governance

Accepted for local MVP, 2026-09-21.

1. Community is generic; City belongs to Community because city governance
   is ItmoCraft domain data, not another independently joined community.
2. Authorization roles are bounded and differ from positions (Мэр,
   Архитектор). Renaming a position never changes permissions.
3. Manager membership is the single governance source. No owner_id that can
   disagree with the roster. Manager elevation is moderator-only in MVP.
4. Public profile is separate from Account and opt-in, retaining the legacy
   private UserProfile intact. Future Minecraft UUID should become canonical
   game identity; memberships already reference User rather than mutable nick.
5. No generic ACL, event bus, workflow or microservice. Concrete policy and
   services inside the Django monolith are sufficient and testable.
6. BlueMap starts with a backend-generated link, without iframe or live sync.

## Verified BlueMap link

On 2026-09-21 opened https://map.joutak.ru in a browser. Initial viewer URL:
`https://map.joutak.ru/#joutak:0:0:0:1500:0:0:0:1:flat`.
Changed the visible X and Z inputs to 1240 and -438; viewer produced:
`https://map.joutak.ru/#joutak:1240:0:-438:1500:0:0:0:1:flat`.
Use this observed flat view template, keeping its Y/camera state fixed at 0;
city altitude is displayed as metadata. Map IDs must come from a configured
allowlist. `joutak` is the only deployment map verified here. Never guess
world-to-map mappings. Missing location means no CTA. With one configured map and the standard overworld,
the backend selects that verified map automatically; multiple-map deployment
requires explicit mapping rather than a UI technical identifier.

Base origin defaults to `https://map.joutak.ru`, configured by
`ITMOCRAFT_MAP_BASE_URL`; validate HTTPS/no credentials/path/query/fragment.
Editors cannot supply arbitrary map URLs. No network calls on city reads.
Unavailable BlueMap does not prevent city pages working.

## Future adapter

Put marker integration in `cities/integrations/`. Django city facts remain
authoritative. A future command/job can upsert/remove a marker keyed by
stable city ID in a dedicated marker-set. Static map-config markers or a
server plugin using BlueMap API are documented approaches:
https://bluemap.bluecolored.de/wiki/customization/Markers.html .
Marker label/description must escape user input and link back to the city.
Use idempotent retries, record sync failure/time separately, never roll back
a saved city because the map is unavailable. No direct writes to existing
production marker sets. Plugin transport/credentials require a later ADR.

## Pasting a viewer link

The deployed BlueMap 5.3 client (`assets/index-58a9319d.js`, `loadPageAddress`)
was inspected on 2026-09-21. Its fragment has ten colon-separated parts: map,
camera X/Y/Z, distance, rotation, angle, tilt, orthographic state, view mode.
Import validates the configured HTTPS origin, root path, no query/credentials,
known map, finite bounded numbers and flat/free/perspective mode. X/Z are rounded
to integer Minecraft coordinates. Camera Y is deliberately discarded. No URL is
fetched by the server; existing canonical generation owns the outgoing link.

Map perimeter/area cannot be inferred from one location. A future region adapter
needs a stable marker/region-to-city mapping before scheduled synchronization.
