from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_emailverificationtask_next_allowed_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="emailverificationtask",
            name="error_category",
            field=models.CharField(
                blank=True,
                choices=[
                    ("smtp_unavailable", "SMTP-сервер недоступен"),
                    ("message_rejected", "Письмо отклонено сервером"),
                    ("internal_error", "Внутренняя ошибка отправки"),
                    ("worker_interrupted", "Воркер прервал отправку"),
                ],
                default=None,
                max_length=32,
                null=True,
            ),
        ),
    ]
