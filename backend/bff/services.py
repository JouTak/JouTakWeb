from __future__ import annotations

from accounts.services.auth import AuthService
from django.http import HttpRequest
from featureflags.registry import get_flags_for_page
from featureflags.services import RequestEvaluationContext, evaluate_many

LEGACY_HOMEPAGE = {
    "hero": {
        "title": "JouTak",
        "description": (
            "Джоутек — колыбель итмокрафта. Запускавшийся парой школьников "
            "как летсплей в 2018 году, этот сервер смог пройти сквозь года "
            "без вайпов, сохранить память и честность."
        ),
        "server_ip": "mc.joutak.ru",
        "primary_cta": {
            "label": "Зарегистрироваться на приватном сервере",
            "href": "https://forms.yandex.ru/u/6501f64f43f74f18a8da28de/",
        },
        "secondary_cta": {
            "label": "Оплатить проходку",
            "to": "/joutak/pay",
        },
    },
    "carousel": [
        {
            "src": "https://cloud.joutak.ru/s/2oQALeqNkndEQMw/preview",
            "alt": "Центральный район сервера",
        },
        {
            "src": "https://cloud.joutak.ru/s/fAn6tq8jn3wcbzy/preview",
            "alt": "Большой гриб на нулевых координатах",
        },
        {
            "src": "https://cloud.joutak.ru/s/oD9SmGSnqGCYqLP/preview",
            "alt": "Летучий Голландец в Казахстане",
        },
        {
            "src": "https://cloud.joutak.ru/s/D8MH8Bmia4f6Ab5/preview",
            "alt": "Крупная сходка новых игроков 2025",
        },
        {
            "src": "https://cloud.joutak.ru/s/3ebFJexTFSntZmL/preview",
            "alt": "Центральный хаб в Нижнем мире",
        },
    ],
}

V2_HOMEPAGE = {
    "hero": {
        "eyebrow": "JouTak Community",
        "title": "Новая главная для поэтапного rollout",
        "description": (
            "Обновлённая версия главной собирает проекты сообщества, события, "
            "галерею и ответы на частые вопросы в одном сценарии."
        ),
        "server_ip": "mc.joutak.ru",
        "primary_cta": {
            "label": "Подать заявку",
            "href": "https://forms.yandex.ru/u/6501f64f43f74f18a8da28de/",
        },
        "secondary_cta": {
            "label": "Оплатить проходку",
            "to": "/joutak/pay",
        },
    },
    "projects": [
        {
            "title": "JouTak SMP",
            "description": (
                "Приватный survival-мир без вайпов и донатных привилегий."
            ),
            "path": "/joutak",
        },
        {
            "title": "ITMOcraft",
            "description": (
                "Университетское комьюнити вокруг Minecraft и "
                "совместных ивентов."
            ),
            "path": "/itmocraft",
        },
        {
            "title": "miniGAMES",
            "description": (
                "Небольшие режимы, быстрые игровые сессии и "
                "внутренняя тусовка."
            ),
            "path": "/minigames",
        },
        {
            "title": "Legacy",
            "description": (
                "Исторический срез проекта и старые пространства сообщества."
            ),
            "path": "/legacy",
        },
    ],
    "events": [
        "Сезонные ивенты и городские сборы игроков.",
        "Командные стройки и общественные проекты.",
        "Внутреннее тестирование новых интерфейсов и механик.",
    ],
    "gallery": [
        "https://cloud.joutak.ru/s/2oQALeqNkndEQMw/preview",
        "https://cloud.joutak.ru/s/fAn6tq8jn3wcbzy/preview",
        "https://cloud.joutak.ru/s/D8MH8Bmia4f6Ab5/preview",
    ],
    "faq": [
        {
            "question": "Зачем новая версия сайта?",
            "answer": (
                "Чтобы постепенно выкатывать новый UX и не ломать "
                "основной поток пользователей."
            ),
        },
        {
            "question": "Как попасть на приват?",
            "answer": (
                "Через заявку, после которой команда проверяет профиль "
                "и доступ."
            ),
        },
        {
            "question": "Что будет с legacy-версией?",
            "answer": (
                "Она остаётся fallback-версией, пока rollout новой "
                "главной не станет основным."
            ),
        },
    ],
}


def viewer_summary(
    request: HttpRequest, user: object | None
) -> dict[str, object]:
    if not user or not getattr(user, "is_authenticated", False):
        return {
            "is_authenticated": False,
            "username": None,
            "email": None,
            "profile_state": "guest",
        }
    profile = AuthService.profile(user)
    return {
        "is_authenticated": True,
        "username": profile.username,
        "email": profile.email,
        "profile_state": profile.profile_state,
        "profile_complete": profile.profile_complete,
        "personalization_context": profile.personalization_context,
    }


def build_bootstrap_payload(
    request: HttpRequest,
    context: RequestEvaluationContext,
) -> dict[str, object]:
    keys = get_flags_for_page(context.page)
    features = evaluate_many(context, keys)
    return {
        "viewer": viewer_summary(request, context.user),
        "features": features,
        "experiments": {
            "anonymous_id_present": bool(context.anonymous_id),
        },
        "layout": {
            "default_project": "jou_tak",
            "homepage_variant": features.get(
                "site_homepage_version", "legacy"
            ),
        },
    }


def build_home_payload(context: RequestEvaluationContext) -> dict[str, object]:
    keys = get_flags_for_page(context.page)
    features = evaluate_many(context, keys)
    variant = str(features.get("site_homepage_version", "legacy"))
    payload = LEGACY_HOMEPAGE if variant == "legacy" else V2_HOMEPAGE
    return {
        "variant": variant,
        "content": payload,
        "features": features,
    }


def build_account_summary_payload(
    request: HttpRequest,
    context: RequestEvaluationContext,
) -> dict[str, object]:
    keys = get_flags_for_page(context.page)
    return {
        "viewer": viewer_summary(request, context.user),
        "features": evaluate_many(context, keys),
    }
