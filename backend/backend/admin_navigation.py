from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

AdminApp = Mapping[str, Any]
AdminModel = Mapping[str, Any]


_GROUP_ORDER = (
    "rollouts",
    "audiences",
    "accounts",
    "system",
)

_GROUP_TITLES = {
    "rollouts": "Раскатки",
    "audiences": "Аудитории",
    "accounts": "Аккаунты",
    "system": "Система",
}

_MODEL_GROUPS = {
    "featureflags.featuredefinition": "rollouts",
    "featureflags.featurerule": "rollouts",
    "featureflags.featureoverride": "rollouts",
    "featureflags.featuregroup": "audiences",
    "auth.user": "accounts",
    "core.userprofile": "accounts",
    "account.emailaddress": "accounts",
    "socialaccount.socialaccount": "accounts",
}

_MODEL_TITLES = {
    "featureflags.featuredefinition": "Функции",
    "featureflags.featurerule": "Раскатки",
    "featureflags.featuregroup": "Аудитории",
    "auth.group": "Роли доступа",
    "featureflags.featureoverride": "Экстренные исключения",
    "featureflags.experimentassignment": "Системные назначения",
    "auth.user": "Аккаунты",
}

_MODEL_ORDER = {
    "featureflags.featuredefinition": 10,
    "featureflags.featurerule": 20,
    "featureflags.featureoverride": 30,
    "featureflags.featuregroup": 10,
    "auth.user": 10,
    "core.userprofile": 20,
    "account.emailaddress": 30,
    "socialaccount.socialaccount": 40,
    "auth.group": 10,
    "featureflags.experimentassignment": 20,
}


def _model_label(app_label: str, model: AdminModel) -> str:
    model_class = model.get("model")
    model_meta = getattr(model_class, "_meta", None)
    label_lower = getattr(model_meta, "label_lower", None)
    if label_lower:
        return str(label_lower).lower()
    return f"{app_label}.{model.get('object_name', '')}".lower()


def build_navigation_app_list(
    app_list: Iterable[AdminApp],
    *,
    rollout_console: AdminModel | None = None,
) -> list[dict]:
    """Regroup Django's already-authorized admin app list for operators.

    ``AdminSite.get_app_list()`` applies ``has_module_permission()`` and the
    model-level permissions before this helper is called. This function only
    changes presentation and therefore must not be used as an authorization
    boundary. The optional process-oriented console item must be authorized
    by the caller before it is supplied.
    """

    grouped_models: dict[str, list[tuple[int, str, dict]]] = {
        group: [] for group in _GROUP_ORDER
    }

    for app in app_list:
        app_label = str(app.get("app_label", ""))
        for source_model in app.get("models", ()):
            label = _model_label(app_label, source_model)
            group = _MODEL_GROUPS.get(label, "system")
            model = dict(source_model)
            model["name"] = _MODEL_TITLES.get(label, model.get("name", ""))
            grouped_models[group].append(
                (
                    _MODEL_ORDER.get(label, 1000),
                    str(model["name"]).casefold(),
                    model,
                )
            )

    if rollout_console is not None:
        console = dict(rollout_console)
        grouped_models["rollouts"].append(
            (0, str(console.get("name", "")).casefold(), console)
        )

    navigation: list[dict] = []
    for group in _GROUP_ORDER:
        ordered_models = [
            model
            for _rank, _name, model in sorted(
                grouped_models[group], key=lambda item: (item[0], item[1])
            )
        ]
        if not ordered_models:
            continue
        navigation.append(
            {
                "name": _GROUP_TITLES[group],
                "app_label": f"joutak-{group}",
                "app_url": None,
                "has_module_perms": True,
                "models": ordered_models,
                "is_navigation_group": True,
            }
        )

    return navigation
