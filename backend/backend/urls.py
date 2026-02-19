from accounts.api.exception_handlers import install_http_error_handler
from accounts.api.router import account_router
from accounts.api.router_auth import auth_router
from accounts.api.router_headless import headless_router
from accounts.api.router_oauth import router_oauth
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.urls import path
from ninja import NinjaAPI

api = NinjaAPI(title="JouTak Auth API")
install_http_error_handler(api)
api.add_router("/account", account_router)
api.add_router("/auth", auth_router)
api.add_router("/auth", headless_router)
api.add_router("/oauth", router_oauth)


def health(_request):
    return HttpResponse("Alive", content_type="text/plain", status=200)


urlpatterns = [
    path("health/", health),
    path("api/", api.urls),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
