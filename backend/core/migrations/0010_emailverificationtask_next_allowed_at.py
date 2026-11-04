from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_emailverificationtask_retry_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailverificationtask',
            name='next_allowed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
