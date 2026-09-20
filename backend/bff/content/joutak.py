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
                "type": "actions",
                "eyebrow": "JouTak SMP",
                "title": "Подключиться к серверу",
                "description": (
                    "JouTak — приватный мир без вайпов, сохранивший память "
                    "сообщества. Подай заявку, подключайся по адресу сервера "
                    "и используй оплату только для взноса за доступ."
                ),
                "facts": [
                    {
                        "id": "server-address",
                        "label": "Адрес сервера",
                        "value": "mc.joutak.ru",
                    }
                ],
                "items": [
                    {
                        "id": "private-server-application",
                        "label": "Зарегистрироваться",
                        "emphasis": "primary",
                        "action": {
                            "kind": "external",
                            "href": (
                                "https://forms.yandex.ru/u/"
                                "6501f64f43f74f18a8da28de/"
                            ),
                        },
                    },
                    {
                        "id": "access-payment",
                        "label": "Оплатить доступ",
                        "emphasis": "secondary",
                        "action": {
                            "kind": "internal",
                            "path": "/joutak/pay",
                        },
                    },
                ],
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
