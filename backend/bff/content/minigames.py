MINIGAMES_CONTENT = {
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
                    "id": "minigames.hero.background",
                    "alt": "",
                },
                "logo": {
                    "kind": "asset",
                    "id": "minigames.logo",
                    "alt": "MiniGames",
                },
                "title": "MiniGames",
            },
            {
                "type": "actions",
                "eyebrow": "MiniGames",
                "title": "Играть и участвовать",
                "description": (
                    "Block Party, Ace Race и Survival Games доступны на "
                    "сервере ITMOcraft. Вступай в беседу, регистрируйся на "
                    "спартакиаду и заранее проверь регламент."
                ),
                "facts": [
                    {
                        "id": "server-address",
                        "label": "Адрес сервера",
                        "value": "craft.itmo.ru",
                    }
                ],
                "items": [
                    {
                        "id": "community-chat",
                        "label": "Вступить в беседу",
                        "emphasis": "primary",
                        "action": {
                            "kind": "external",
                            "href": (
                                "https://vk.me/join/"
                                "WDyZMd4pF8Xhu/egqaDnrHmbajAmm0cZ2og="
                            ),
                        },
                    },
                    {
                        "id": "spartakiad-registration",
                        "label": "Зарегистрироваться",
                        "emphasis": "secondary",
                        "action": {
                            "kind": "external",
                            "href": (
                                "https://docs.google.com/forms/d/e/"
                                "1FAIpQLSfX7C2f1WII6Ak_me3onbRAcb71MSEap51MS-"
                                "Hic4XYg915MA/viewform"
                            ),
                        },
                    },
                    {
                        "id": "spartakiad-rules",
                        "label": "Читать регламент",
                        "emphasis": "tertiary",
                        "action": {
                            "kind": "external",
                            "href": (
                                "https://docs.google.com/document/d/"
                                "1TasKKNFDkostGTnX0SsSpCzvgKw7tITA/edit?tab=t.0"
                            ),
                        },
                    },
                    {
                        "id": "esports-partner",
                        "label": "Кронверкские барсы",
                        "emphasis": "tertiary",
                        "action": {
                            "kind": "external",
                            "href": "https://vk.com/kb_esports",
                        },
                    },
                ],
            },
            {
                "type": "projects",
                "title": "Режимы",
                "items": [
                    {
                        "id": "block-party",
                        "title": "Block Party",
                        "description": (
                            "Найди блок нужного цвета до исчезновения пола."
                        ),
                        "image": {
                            "kind": "asset",
                            "id": "minigames.block-party",
                            "alt": "Block Party",
                        },
                        "action": {
                            "kind": "internal",
                            "path": "/minigames",
                        },
                    }
                ],
            },
        ],
    },
}
