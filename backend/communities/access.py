from accounts.api.errors import raise_structured_error
from accounts.services.sessions import SessionService
from allauth.headless.contrib.ninja.security import x_session_token_auth
from featureflags.registry import HUB_FLAG_KEYS
from featureflags.services import RequestEvaluationContext, evaluate_many


def actor_for(request, *, required=False):
    # Mutations intentionally use session-token auth, never cookie auth.
    user = x_session_token_auth(request)
    request.auth = user
    if user:
        SessionService.assert_session_allowed(request)
        if not user.is_active:
            user = None
    if required and not user:
        raise_structured_error(
            401, detail="Войдите в аккаунт.", error_code="AUTH_REQUIRED"
        )
    return user


def flags_for(user):
    return evaluate_many(RequestEvaluationContext(user=user), HUB_FLAG_KEYS)


def require_flags(user, *keys):
    flags = flags_for(user)
    if not all(flags.get(key) is True for key in keys):
        raise_structured_error(
            404, detail="Раздел недоступен.", error_code="FEATURE_DISABLED"
        )
    return flags


def authenticated(user):
    return bool(user and user.is_authenticated and user.is_active)
