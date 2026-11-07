from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_emailverificationtask'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailverificationtask',
            name='kind',
            field=models.CharField(choices=[('email_confirmation', 'Подтверждение почты'), ('email_confirmation_signup', 'Подтверждение почты при регистрации'), ('password_reset', 'Восстановление пароля')], default='email_confirmation', max_length=32),
        ),
        migrations.AlterField(
            model_name='emailverificationtask',
            name='status',
            field=models.CharField(choices=[('waiting', 'В очереди'), ('retrying', 'Повторная попытка (ошибка SMTP)'), ('sent', 'Отправлено'), ('error', 'Ошибка отправки'), ('cancelled', 'Отменено')], default='waiting', max_length=16),
        ),
    ]
