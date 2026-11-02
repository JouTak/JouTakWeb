# Authorization

Platform moderator = active authenticated user with `cities.moderate_city`
Django permission, or superuser. `is_staff` alone grants no governance power.
Community role and city role are scoped to their memberships. Only ACTIVE
membership + ACTIVE parent community confers city powers.

| Action | Guest | Resident | Representative | Manager | Moderator / superuser |
| --- | --- | --- | --- | --- | --- |
| Public active city | yes | yes | yes | yes | yes |
| Own memberships | no | yes | yes | yes | yes |
| Description / contacts / presentation | no | no | yes | yes | yes |
| Coordinates / recruitment / facts | no | no | no | yes | yes |
| Invite/revoke resident invitation | no | no | no | yes | yes |
| Accept/decline own invitation | no | recipient only | recipient only | recipient only | recipient only |
| Roster and positions | no | no | no | yes | yes |
| Assign representative | no | no | no | yes | yes |
| Assign/demote manager | no | no | no | no | yes |
| Create / archive / restore lifecycle | no | no | no | no | yes |
| History | no | no | yes | yes | yes |
| Last manager override | no | no | no | no | explicit reason |
| Rollback | deferred | deferred | deferred | deferred | deferred |

Managers cannot remove/demote another manager. Last ACTIVE manager may not
leave a non-archived city. Moderator override must include a reason and is
recorded; account self-deletion has no override. All membership mutations
lock the city before counting managers, so two concurrent demotions cannot
both pass. Member identifiers are looked up inside the specified city.

City capabilities are returned for UX; services independently recompute them.
Archived cities are moderator-only and preserved. Draft city is visible to
its editors and moderators. Feature flags gate endpoints in addition to RBAC.

Visibility is enforced in serializers, never only hidden in React. Leadership
degrades to a position without a profile link when publication is disabled.
Public resident lists are paged and include only ACTIVE users whose profile,
profile relationship policy, and city membership permit the requesting audience.
The management roster remains separately authorized.

Private city contacts mean city editors only (not a personal secret of the
author). Community contacts require ACTIVE parent membership. Private profile
fields are self-only. City membership publication requires both the person
allowing membership visibility on their profile and the relationship visibility.
Moderator override is available through the typed API with `override_reason`;
the UI requires a transfer and does not expose the emergency override action.
