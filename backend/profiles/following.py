from ninja import Schema

from profiles.connection_schemas import PlayerOut
from profiles.connections import accessible_players, page_out, unavailable
from profiles.models import ProfileFollow


class OwnFollowOut(Schema):
    id: int
    profile: PlayerOut | None


class OwnFollowingOut(Schema):
    items: list[OwnFollowOut]
    page: int
    total: int


def own_following(actor, page):
    query = ProfileFollow.objects.filter(user=actor).order_by(
        "-created_at", "pk"
    )
    rows = list(query[(page - 1) * 24 : page * 24])
    users = accessible_players(actor).filter(
        pk__in=[row.target_id for row in rows]
    )
    names = dict(users.values_list("pk", "username"))
    profiles = {p.username: p for p in page_out(users, actor, 1).items}
    return OwnFollowingOut(
        items=[
            OwnFollowOut(
                id=row.pk, profile=profiles.get(names.get(row.target_id))
            )
            for row in rows
        ],
        page=page,
        total=query.count(),
    )


def remove_own_follow(actor, relation_id):
    removed, _ = ProfileFollow.objects.filter(
        user=actor, pk=relation_id
    ).delete()
    if not removed:
        unavailable()
    return {"is_following": False}
