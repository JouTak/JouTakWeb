from importlib import import_module

from django.apps import AppConfig


class PlayerGroupsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "playergroups"
    verbose_name = "Объединения игроков"

    def ready(self):
        import_module("playergroups.signals")
