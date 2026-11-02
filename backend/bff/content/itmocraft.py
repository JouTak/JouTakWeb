ITMOCRAFT_CONTENT = {
    "legacy": {
        "template": "landing-legacy",
        "sections": [],
    },
    "v2": {
        "template": "landing-v2",
        "sections": [
            {
                "type": "hero",
                "background": {
                    "kind": "asset",
                    "id": "itmocraft.hero.background",
                    "alt": "",
                },
                "logo": {
                    "kind": "asset",
                    "id": "itmocraft.logo",
                    "alt": "ITMOcraft",
                },
                "eyebrow": "Комьюнити",
                "title": "Больше, чем просто сервер!",
            },
            {
                "type": "actions",
                "eyebrow": "Команда ITMOcraft",
                "title": "Стать частью сообщества",
                "description": (
                    "Оргсостав ITMOcraft разрабатывает плагины, строит "
                    "ивенты и создаёт медиа. Если хочешь участвовать — "
                    "оставь заявку в команду организаторов."
                ),
                "items": [
                    {
                        "id": "organizer-application",
                        "label": "Подать заявку в команду",
                        "emphasis": "primary",
                        "action": {
                            "kind": "external",
                            "href": (
                                "https://forms.yandex.ru/u/"
                                "67773408068ff0452320c8b4/"
                            ),
                        },
                    }
                ],
            },
            {
                "type": "events",
                "title": "События",
                "items": [
                    {
                        "id": "bunker",
                        "title": "Бункер",
                        "description": (
                            "Прототип карточки события для "
                            "дизайн-тестирования."
                        ),
                        "location": "JouTak",
                        "image": {
                            "kind": "asset",
                            "id": "events.bunker",
                            "alt": "Бункер",
                        },
                        "starts_at": "2026-02-28T19:00:00+03:00",
                        "action": {
                            "kind": "design_placeholder",
                            "id": "bunker-details",
                            "behavior": "no_op",
                        },
                        "action_label": "Регистрация скоро",
                    }
                ],
            },
        ],
    },
}
