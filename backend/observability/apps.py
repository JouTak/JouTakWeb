from django.apps import AppConfig
from django.utils.module_loading import import_string


class ObservabilityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "observability"
    verbose_name = "Observability"

    def ready(self) -> None:
        setup_observability = import_string(
            "observability.setup.setup_observability"
        )
        setup_observability()
