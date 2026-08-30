from django.urls import path

from bff import views

urlpatterns = [
    path("bootstrap", views.bootstrap),
    path("account/summary", views.account_summary),
    path("pages/contact", views.contact),
    path("pages/minigames", views.minigames),
    path("pages/itmocraft", views.itmocraft),
    path("pages/itmocraft/legacy", views.itmocraft_legacy),
    path("pages/joutak", views.joutak),
    path("feature-overrides", views.feature_overrides),
]
