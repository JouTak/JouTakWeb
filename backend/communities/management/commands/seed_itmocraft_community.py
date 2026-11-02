from django.core.management.base import BaseCommand

from communities.models import Community


class Command(BaseCommand):
    help = (
        "Create JouTak SMP with its stable itmocraft slug; "
        "preserve custom content."
    )

    def handle(self, *args, **options):
        community, created = Community.objects.get_or_create(
            slug="itmocraft",
            defaults={
                "name": "JouTak SMP",
                "short_description": (
                    "Сервер выживания JouTak: игроки, города и общий мир."
                ),
            },
        )
        if community.name.lower() == "itmocraft":
            community.name = "JouTak SMP"
            community.save(update_fields=["name", "updated_at"])
        self.stdout.write(
            f"{community.slug}: {'created' if created else 'exists'}"
        )
