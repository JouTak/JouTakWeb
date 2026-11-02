from importlib import import_module

from django.apps import AppConfig


class CitiesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "cities"

    def ready(self):
        import_module("cities.signals")
