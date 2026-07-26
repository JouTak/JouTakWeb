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
