from django.db import migrations, models


class Migration(migrations.Migration):
    """Track refresh-token expiry on `UserSessionToken` directly.

    Allows `cleanup_auth_data` and ops tooling to purge expired refresh
    mappings with a single indexed filter instead of joining against
    `OutstandingToken`. Nullable so existing rows stay valid without a
    data backfill — they'll be pruned by the generic blacklist/revoked
    paths until they're replaced on the next refresh.
    """

    dependencies = [
        ("core", "0004_session_token_digest"),
    ]

    operations = [
        migrations.AddField(
            model_name="usersessiontoken",
            name="expires_at",
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                null=True,
            ),
        ),
    ]
