import importlib

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    verbose_name = "Модуль конфигурации Аккаунтов"

    def ready(self) -> None:
        importlib.import_module("accounts.signals")


__all__ = ["AccountsConfig"]
