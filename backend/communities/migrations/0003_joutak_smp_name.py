from django.db import migrations


def rename_server(apps, schema_editor):
    Community = apps.get_model("communities", "Community")
    query = Community.objects.using(schema_editor.connection.alias).filter(
        slug="itmocraft"
    )
    query.filter(name__iexact="itmocraft").update(name="JouTak SMP")
    query.filter(short_description="Люди, города и мир ItmoCraft").update(
        short_description="Сервер выживания JouTak: игроки, города и общий мир."
    )


class Migration(migrations.Migration):
    dependencies = [
        (
            "communities",
            "0002_community_enrollment_text_community_enrollment_url",
        ),
    ]
    operations = [
        migrations.RunPython(rename_server, migrations.RunPython.noop)
    ]
