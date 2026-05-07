from django.contrib.admin.apps import AdminConfig


class JouTakAdminConfig(AdminConfig):
    default_site = "backend.admin_site.JouTakAdminSite"
