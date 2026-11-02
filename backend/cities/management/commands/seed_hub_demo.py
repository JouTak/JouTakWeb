import os
import secrets

from accounts.services.email_addresses import sync_user_email_address
from communities.models import Community, CommunityMembership
from core.models import UserProfile
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from featureflags.models import FeatureDefinition, FeatureRule
from featureflags.registry import HUB_FLAG_KEYS
from profiles.models import CommunityProfile

from cities.models import City, CityMembership
from cities.schemas import CityCreate
from cities.services import create_city


class Command(BaseCommand):
    help = "Seed isolated local hub personas/cities; never use on production."

    def add_arguments(self, parser):
        parser.add_argument("--enable-hub", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        if (
            not settings.DEBUG
            or str(settings.DATABASES["default"]["NAME"])
            != str(
                settings.BASE_DIR.parent / ".local" / "community-hub.sqlite3"
            )
            or not getattr(settings, "HUB_DEMO_MODE", False)
        ):
            raise CommandError(
                "Use --settings backend.settings.hub_demo (isolated database)."
            )
        call_command("seed_itmocraft_community", stdout=self.stdout)
        call_command("sync_feature_registry", stdout=self.stdout)
        community = Community.objects.get(slug="itmocraft")
        password = os.environ.get(
            "HUB_DEMO_PASSWORD"
        ) or secrets.token_urlsafe(18)
        users = {}
        created_users = []
        for role in ("resident", "representative", "manager", "moderator"):
            username = f"hub_{role}"
            user, created = get_user_model().objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@example.local",
                    "is_staff": role == "moderator",
                },
            )
            if user.email != f"{username}@example.local":
                raise CommandError(
                    "Demo username conflicts with existing account."
                )
            if created:
                user.set_password(password)
                user.save()
                created_users.append(username)
            sync_user_email_address(user)
            user.emailaddress_set.update(verified=True)
            CommunityMembership.objects.get_or_create(
                user=user, community=community, defaults={"status": "active"}
            )
            UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    "minecraft_nick": f"Hub{role.title()}"[:16],
                    "vk_username": username,
                    "minecraft_has_license": True,
                    "is_itmo_student": False,
                },
            )
            CommunityProfile.objects.get_or_create(
                user=user,
                defaults={
                    "display_name": {
                        "manager": "Алекс · управляющий",
                        "resident": "Саша · житель",
                        "representative": "Мира · представитель",
                        "moderator": "Модератор JouTak",
                    }[role],
                    "visibility": "public",
                    "minecraft_visibility": "public",
                    "memberships_visibility": "public",
                    "bio": "Демонстрационный профиль Community Hub.",
                },
            )
            users[role] = user
        users["moderator"].user_permissions.add(
            Permission.objects.get(
                content_type__app_label="cities", codename="moderate_city"
            )
        )
        created_city_slugs = []
        for slug, name, description in (
            (
                "city-alpha",
                "Альфа",
                "Город у реки. Строим вместе и встречаем новых соседей.",
            ),
            (
                "city-beta",
                "Бета",
                "Тихий город для больших архитектурных идей.",
            ),
        ):
            if not City.objects.filter(slug=slug).exists():
                created_city_slugs.append(slug)
                create_city(
                    users["moderator"],
                    CityCreate(
                        community_slug="itmocraft",
                        slug=slug,
                        name=name,
                        short_description=description,
                        manager_username=users["manager"].username,
                        status="active",
                        recruitment_status="open"
                        if slug == "city-alpha"
                        else "limited",
                        description=(
                            "## Наш город\n\n"
                            "Здесь каждый может найти свой проект. "
                            "Общие пространства, спокойные улицы "
                            "и помощь соседям."
                        ),
                        how_to_join=(
                            "Свяжитесь с представителем города "
                            "и расскажите, что хотите построить."
                        ),
                        location={
                            "world": "overworld",
                            "x": 1240,
                            "z": -438,
                            "map_id": "joutak",
                        }
                        if slug == "city-alpha"
                        else None,
                    ),
                )
        city = City.objects.get(slug="city-alpha")
        for role in ("resident", "representative"):
            CityMembership.objects.get_or_create(
                city=city,
                user=users[role],
                defaults={
                    "role": role,
                    "status": "active",
                    "visibility": "public",
                },
            )
        CityMembership.objects.filter(
            user=users["manager"], city__slug__in=created_city_slugs
        ).update(visibility="public", position="Мэр")
        if options["enable_hub"]:
            for key in HUB_FLAG_KEYS:
                FeatureRule.objects.get_or_create(
                    feature=FeatureDefinition.objects.get(key=key),
                    name="Local hub demo",
                    defaults={
                        "rule_type": "everyone",
                        "value": "true",
                        "priority": 10,
                    },
                )
        self.stdout.write(
            "Personas: " + ", ".join(user.email for user in users.values())
        )
        if created_users:
            self.stdout.write(
                "Password for newly created personas: " + password
            )
        else:
            self.stdout.write("Existing demo passwords were preserved.")
