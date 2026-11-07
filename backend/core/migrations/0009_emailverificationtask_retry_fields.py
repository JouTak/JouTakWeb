from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_emailverificationtask_kind_cancelled'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailverificationtask',
            name='attempts',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='emailverificationtask',
            name='last_error',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
        migrations.AddField(
            model_name='emailverificationtask',
            name='locked_until',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
