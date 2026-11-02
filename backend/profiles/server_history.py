from functools import lru_cache

from django.utils import timezone
from pymorphy3 import MorphAnalyzer

from profiles.policy import visible
from profiles.schemas import ServerHistoryOut


@lru_cache(maxsize=1)
def day_word():
    # Load the dictionary lazily, once per process.
    return MorphAnalyzer(lang="ru").parse("день")[0]


def server_history(profile, *, own=False, shared=False):
    first_joined = profile.minecraft_first_joined_at
    if not visible(profile.minecraft_visibility, own=own, shared=shared):
        return None
    first_date = timezone.localdate(first_joined)
    days = (timezone.localdate() - first_date).days
    if days < 0:
        return None
    noun = day_word().make_agree_with_number(days).word
    return ServerHistoryOut(
        first_joined_on=first_date,
        days=days,
        days_text=f"{days} {noun}",
    )
