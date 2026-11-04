from django.apps import AppConfig
from django.db.models.signals import post_migrate

EMAIL_DISPATCH_SCHEDULE_NAME = "accounts-email-dispatch"


def ensure_email_dispatch_schedule(sender, **kwargs) -> None:
    """Make sure the periodic e-mail retry dispatcher is scheduled.

    Runs after ``migrate`` (once all django-q tables exist). The schedule
    is picked up by the ``qcluster`` worker, so deploys need no manual
    step. An existing schedule (and any edits made to it) is kept.
    """
    if sender.label != "django_q":
        return
    schedule_model = sender.apps.get_model("django_q", "Schedule")
    schedule_model.objects.get_or_create(
        name=EMAIL_DISPATCH_SCHEDULE_NAME,
        defaults={
            "func": "accounts.tasks.dispatch_due_emails",
            "schedule_type": schedule_model.MINUTES,
            "minutes": 1,
            "repeats": -1,
        },
    )


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    verbose_name = "Модуль конфигурации Аккаунтов"

    def ready(self) -> None:
        # Imported here: the handlers need the models, which are not
        # loaded yet when this module is imported.
        from accounts import signals  # noqa: F401, PLC0415

        post_migrate.connect(
            ensure_email_dispatch_schedule,
            dispatch_uid="accounts.ensure_email_dispatch_schedule",
        )


__all__ = ["AccountsConfig", "EMAIL_DISPATCH_SCHEDULE_NAME"]
