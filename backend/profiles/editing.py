from accounts.api.errors import raise_structured_error

from profiles.models import CommunityProfile


def check_version(actual, expected):
    if actual != expected:
        raise_structured_error(
            409,
            detail="Данные изменены в другой вкладке. Загрузите актуальные "
            "значения и сверьте их со своими изменениями.",
            error_code="PROFILE_VERSION_CONFLICT",
        )


def locked_profile(user):
    # Caller holds the User lock, including when no profile exists yet.
    return CommunityProfile.objects.get_or_create(user=user)[0]
