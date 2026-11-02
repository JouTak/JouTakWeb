from accounts.api.exception_handlers import install_http_error_handler
from accounts.api.router import account_router
from accounts.api.router_auth import auth_router
from accounts.api.router_oauth import router_oauth
from cities.api import router as cities_router
from cities.invitation_api import account_router as invitation_account_router
from cities.invitation_api import router as invitation_router
from cities.moderation import router as moderation_router
from communities.api import membership_router
from communities.api import router as communities_router
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.urls import include, path
from ninja import NinjaAPI
from playergroups.api import account_router as group_account_router
from playergroups.api import moderation_router as group_moderation_router
from playergroups.api import profile_router as group_profile_router
from playergroups.api import router as groups_router
from profiles.api import router as profiles_router
from profiles.self_api import router as profile_self_router
from profiles.social_api import router as profile_social_router

api = NinjaAPI(title="JouTak Auth API")
install_http_error_handler(api)
api.add_router("/account", account_router)
api.add_router("/auth", auth_router)
api.add_router("/oauth", router_oauth)
api.add_router("/profiles", profiles_router)
api.add_router("/profiles", profile_social_router)
api.add_router("/profiles", profile_self_router)
api.add_router("/communities", communities_router)
api.add_router("/account", membership_router)
api.add_router("/cities", cities_router)
api.add_router("/cities", invitation_router)
api.add_router("/account", invitation_account_router)
api.add_router("/moderation/cities", moderation_router)
api.add_router("/groups", groups_router)
api.add_router("/account", group_account_router)
api.add_router("/profiles", group_profile_router)
api.add_router("/moderation/groups", group_moderation_router)


def health(_request: HttpRequest) -> HttpResponse:
    return HttpResponse("Alive", content_type="text/plain", status=200)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("api/auth/flow/", include("allauth.headless.urls")),
    path("health/", health),
    path("api/", api.urls),
    path("bff/", include("bff.urls")),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
