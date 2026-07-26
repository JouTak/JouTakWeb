JOUTAK_CONTENT = {
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
                    "id": "joutak.hero.background",
                    "alt": "",
                },
                "logo": {
                    "kind": "asset",
                    "id": "joutak.logo",
                    "alt": "JouTak",
                },
                "eyebrow": "Фундамент ITMOcraft",
                "title": "Отсюда всё начиналось!",
            },
            {
                "type": "gallery",
                "title": "Галерея",
                "items": [
                    {
                        "id": "joutak-smp",
                        "label": "JouTak SMP",
                        "cover": {
                            "kind": "asset",
                            "id": "gallery.joutak.cover",
                            "alt": "JouTak SMP",
                        },
                        "photos": [
                            {
                                "kind": "design_placeholder",
                                "id": "joutak-photo-1",
                                "alt": "Согласуемая фотография",
                                "broken": True,
                            }
                        ],
                    }
                ],
            },
        ],
    },
}
