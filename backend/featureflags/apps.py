from django.apps import AppConfig
from django.utils.module_loading import import_string
from openfeature import api


class FeatureFlagsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "featureflags"
    verbose_name = "Feature Flags"

    def ready(self) -> None:
        provider_cls = import_string(
            "featureflags.provider.DjangoAdminFeatureProvider"
        )
        api.set_provider(provider_cls())
