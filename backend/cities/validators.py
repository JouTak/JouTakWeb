from urllib.parse import urlsplit


def validate_contact(contact):
    parsed = urlsplit(contact.url)
    hosts = {
        "discord": {"discord.gg", "discord.com"},
        "telegram": {"t.me"},
        "vk": {"vk.com", "vk.ru"},
    }
    if parsed.hostname not in hosts.get(
        contact.type, set()
    ) or parsed.port not in {None, 443}:
        raise ValueError(
            "Используйте приглашение Discord, ссылку Telegram или VK."
        )
    path = parsed.path.strip("/")
    if not path or (
        contact.type == "discord"
        and parsed.hostname == "discord.com"
        and not path.startswith("invite/")
    ):
        raise ValueError(
            "Укажите ссылку на приглашение или страницу, "
            "а не главную страницу сервиса."
        )
    return contact
