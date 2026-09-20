from __future__ import annotations

from copy import deepcopy

from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase

from backend.admin_navigation import build_navigation_app_list


def _model(object_name: str, name: str, *, view: bool = True) -> dict:
    return {
        "name": name,
        "object_name": object_name,
        "perms": {
            "add": False,
            "change": False,
            "delete": False,
            "view": view,
        },
        "admin_url": f"/admin/example/{object_name.lower()}/",
        "add_url": None,
        "view_only": True,
    }


class AdminNavigationTests(SimpleTestCase):
    def test_groups_and_renames_models_for_backoffice_tasks(self):
        app_list = [
            {
                "app_label": "auth",
                "models": [
                    _model("Group", "группы"),
                    _model("User", "пользователи"),
                ],
            },
            {
                "app_label": "featureflags",
                "models": [
                    _model("ExperimentAssignment", "назначения"),
                    _model("FeatureGroup", "группы таргетирования"),
                    _model("FeatureRule", "правила"),
                    _model("FeatureDefinition", "фича-флаги"),
                    _model("FeatureOverride", "переопределения"),
                ],
            },
        ]

        result = build_navigation_app_list(app_list)

        self.assertEqual(
            [group["name"] for group in result],
            ["Раскатки", "Аудитории", "Аккаунты", "Система"],
        )
        self.assertEqual(
            [model["name"] for model in result[0]["models"]],
            ["Функции", "Раскатки", "Экстренные исключения"],
        )
        self.assertEqual(result[1]["models"][0]["name"], "Аудитории")
        self.assertEqual(result[2]["models"][0]["name"], "Аккаунты")
        self.assertEqual(
            [model["name"] for model in result[3]["models"]],
            ["Роли доступа", "Системные назначения"],
        )

    def test_does_not_reintroduce_models_filtered_by_admin_permissions(self):
        app_list = [
            {
                "app_label": "featureflags",
                "models": [_model("FeatureDefinition", "фича-флаги")],
            }
        ]

        result = build_navigation_app_list(app_list)

        self.assertEqual([group["name"] for group in result], ["Раскатки"])
        self.assertEqual(
            [model["object_name"] for model in result[0]["models"]],
            ["FeatureDefinition"],
        )

    def test_preserves_model_urls_and_permission_payload(self):
        model = _model("User", "пользователи")
        model["perms"]["change"] = True
        app_list = [{"app_label": "auth", "models": [model]}]
        original = deepcopy(app_list)

        result = build_navigation_app_list(app_list)

        rendered_model = result[0]["models"][0]
        self.assertEqual(
            rendered_model["perms"],
            original[0]["models"][0]["perms"],
        )
        self.assertEqual(
            rendered_model["admin_url"],
            original[0]["models"][0]["admin_url"],
        )
        self.assertEqual(app_list, original)

    def test_unknown_registered_models_are_kept_in_system_group(self):
        app_list = [
            {
                "app_label": "sites",
                "models": [_model("Site", "сайты")],
            }
        ]

        result = build_navigation_app_list(app_list)

        self.assertEqual([group["name"] for group in result], ["Система"])
        self.assertEqual(result[0]["models"][0]["name"], "сайты")

    def test_navigation_group_heading_is_not_a_broken_application_link(self):
        app_list = build_navigation_app_list(
            [
                {
                    "app_label": "auth",
                    "models": [_model("User", "пользователи")],
                }
            ]
        )

        html = render_to_string(
            "admin/app_list.html",
            {
                "app_list": app_list,
                "request": RequestFactory().get("/admin/"),
                "show_changelinks": True,
            },
        )

        self.assertIn('<span class="section">Аккаунты</span>', html)
        self.assertNotIn('href="None"', html)

    def test_authorized_rollout_console_is_first_without_replacing_functions(
        self,
    ):
        console = {
            "name": "Управление раскатками",
            "object_name": "GuidedRollout",
            "perms": {
                "add": True,
                "change": False,
                "delete": False,
                "view": True,
            },
            "admin_url": "/admin/featureflags/rollouts/",
            "add_url": "/admin/featureflags/rollouts/new/",
            "view_only": True,
        }

        result = build_navigation_app_list(
            [
                {
                    "app_label": "featureflags",
                    "models": [_model("FeatureDefinition", "фича-флаги")],
                }
            ],
            rollout_console=console,
        )

        self.assertEqual(
            [model["name"] for model in result[0]["models"]],
            ["Управление раскатками", "Функции"],
        )
        self.assertEqual(
            result[0]["models"][0]["admin_url"],
            "/admin/featureflags/rollouts/",
        )

    def test_rollout_console_is_not_added_without_authorized_payload(self):
        result = build_navigation_app_list(
            [
                {
                    "app_label": "featureflags",
                    "models": [_model("FeatureDefinition", "фича-флаги")],
                }
            ]
        )

        self.assertEqual(
            [model["name"] for model in result[0]["models"]],
            ["Функции"],
        )
