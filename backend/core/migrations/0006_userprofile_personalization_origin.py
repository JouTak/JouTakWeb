from django.db import migrations, models


def mark_existing_profiles_as_legacy(apps, schema_editor):
    UserProfile = apps.get_model("core", "UserProfile")
    UserProfile.objects.update(personalization_origin="legacy")


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0005_usersessiontoken_expires_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="personalization_origin",
            field=models.CharField(
                choices=[
                    ("signup", "Signup"),
                    ("legacy", "Legacy"),
                ],
                default="signup",
                max_length=16,
            ),
        ),
        migrations.RunPython(
            mark_existing_profiles_as_legacy,
            migrations.RunPython.noop,
        ),
    ]
