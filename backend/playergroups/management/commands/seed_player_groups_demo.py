from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from featureflags.models import FeatureDefinition, FeatureRule

from playergroups import (
    invitations,
    leadership,
    membership_service,
    participation,
    services,
)
from playergroups.models import PlayerGroup
from playergroups.schemas import (
    ApplyIn,
    GroupCreate,
    GroupUpdate,
    JoinIn,
    LifecycleIn,
    OfferIn,
    RoleIn,
)


class Command(BaseCommand):
    help = "Add groups to the isolated Hub demo, preserving existing data."

    def add_arguments(self, parser):
        parser.add_argument("--enable", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        if (
            not settings.DEBUG
            or not getattr(settings, "HUB_DEMO_MODE", False)
            or str(settings.DATABASES["default"]["NAME"])
            != str(
                settings.BASE_DIR.parent / ".local" / "community-hub.sqlite3"
            )
        ):
            raise CommandError(
                "Use the isolated backend.settings.hub_demo database."
            )
        users = {
            role: get_user_model()
            .objects.filter(
                username=f"hub_{role}", email=f"hub_{role}@example.local"
            )
            .first()
            for role in ("manager", "representative", "resident", "moderator")
        }
        if not all(users.values()):
            raise CommandError(
                "Create the existing Hub demo personas first (seed_hub_demo)."
            )
        manager = users["manager"]
        users["moderator"].user_permissions.add(
            Permission.objects.get(
                content_type__app_label="playergroups",
                codename="moderate_playergroup",
            )
        )
        scenarios = [
            (
                "builders-workshop",
                "Мастерская строителей",
                "Обмениваемся идеями и собираем проекты вместе.",
                "club",
                "open",
                "public",
                None,
            ),
            (
                "northern-expedition",
                "Северная экспедиция",
                "Исследуем новые маршруты и готовим совместные походы.",
                "team",
                "approval",
                "public",
                "itmocraft",
            ),
            (
                "redstone-circle",
                "Редстоун-кружок",
                "Небольшая команда для экспериментов с механизмами.",
                "guild",
                "invite_only",
                "private",
                None,
            ),
            (
                "evening-build",
                "Вечерняя стройка",
                "Встречаемся после работы и строим без спешки.",
                "team",
                "invite_only",
                "unlisted",
                None,
            ),
            (
                "summer-project",
                "Летний проект",
                "Сохраняем историю завершённого общего проекта.",
                "club",
                "open",
                "public",
                None,
            ),
            (
                "cartographers",
                "Картографы",
                "Готовим объединение любителей дальних путешествий.",
                "club",
                "approval",
                "public",
                None,
            ),
        ]
        created = []
        for slug, name, summary, category, mode, access, scope in scenarios:
            if PlayerGroup.objects.filter(slug=slug).exists():
                continue
            creator = (
                users["representative"] if slug == "cartographers" else manager
            )
            group = services.create_group(
                creator,
                GroupCreate(
                    slug=slug,
                    name=name,
                    short_description=summary,
                    category=category,
                    scope_slug=scope,
                ),
            )
            group = services.update_group(
                creator,
                slug,
                GroupUpdate(
                    version=group.version,
                    description=(
                        f"## {name}\n\n{summary}\n\n"
                        "Договоритесь о первом совместном проекте."
                    ),
                    rules=(
                        "Уважайте время друг друга и договаривайтесь "
                        "перед изменением чужих построек."
                    ),
                    welcome=(
                        "Представьтесь организаторам и предложите "
                        "идею для первой встречи."
                    ),
                    join_mode=mode,
                    access=access,
                    accepting=True,
                    roster_visibility="public",
                    application_question="Чем хотите заняться вместе?"
                    if mode == "approval"
                    else "",
                ),
            )
            if slug != "cartographers":
                group = services.lifecycle(
                    manager,
                    slug,
                    LifecycleIn(version=group.version, action="publish"),
                )
            if slug == "builders-workshop":
                # Isolated demo personas simulate consenting members.
                for role in ("resident", "representative"):
                    participation.join(
                        users[role], slug, JoinIn(visibility="public")
                    )
                membership_service.change_role(
                    manager,
                    slug,
                    group.memberships.get(user=users["representative"]).pk,
                    RoleIn(role="moderator"),
                )
                leadership.offer(
                    manager,
                    slug,
                    OfferIn(
                        membership_id=group.memberships.get(
                            user=users["resident"]
                        ).pk
                    ),
                )
            if slug == "northern-expedition":
                participation.apply(
                    users["resident"],
                    slug,
                    ApplyIn(answer="Хочу вместе исследовать новые биомы."),
                )
            if slug == "redstone-circle":
                invitations.invite(
                    manager, slug, users["representative"].username
                )
            if slug == "summer-project":
                services.lifecycle(
                    manager,
                    slug,
                    LifecycleIn(version=group.version, action="archive"),
                )
            created.append(slug)
        if options["enable"]:
            call_command("sync_feature_registry", stdout=self.stdout)
            for key in (
                "communities_ui",
                "player_groups_ui",
                "player_groups_write",
            ):
                feature = FeatureDefinition.objects.get(key=key)
                FeatureRule.objects.get_or_create(
                    feature=feature,
                    name="Local player groups demo",
                    defaults={
                        "priority": 1,
                        "rule_type": "everyone",
                        "value": "true",
                        "enabled": True,
                    },
                )
        self.stdout.write(
            f"Created {len(created)} groups. "
            "Existing people, content and participation preserved."
        )
