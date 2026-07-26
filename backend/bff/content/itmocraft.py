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
                            "behavior": "hash",
                        },
                    }
                ],
            },
        ],
    },
}
