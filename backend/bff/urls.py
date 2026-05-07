from django.urls import path

from bff import views

urlpatterns = [
    path("bootstrap", views.bootstrap),
    path("pages/home", views.homepage),
    path("account/summary", views.account_summary),
]
