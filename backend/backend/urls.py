from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from ninja import NinjaAPI
from ninja_jwt.routers.obtain import obtain_pair_router
from ninja_jwt.routers.verify import verify_router
from ninja_jwt.routers.blacklist import blacklist_router

from accounts.api.router import account_router
from accounts.api.router_auth import auth_router
from accounts.api.router_headless import headless_router
from accounts.api.router_oauth import router_oauth
from accounts.api.exception_handlers import install_http_error_handler


api = NinjaAPI(title="JouTak Auth API")
install_http_error_handler(api)
api.add_router("/account", account_router)
api.add_router("/auth", auth_router)
api.add_router("/auth", headless_router)
api.add_router("/oauth", router_oauth)
api.add_router("/token", obtain_pair_router)
api.add_router("/token", verify_router)
api.add_router("/token", blacklist_router)

urlpatterns = [
    path("api/", api.urls),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
