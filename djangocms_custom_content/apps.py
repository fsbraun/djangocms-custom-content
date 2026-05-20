from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CustomContentConfig(AppConfig):
    name = "djangocms_custom_content"
    verbose_name = _("django CMS Custom Content")
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from django.contrib import admin

        from djangocms_custom_content.admin import register_m2m_autocomplete_url

        register_m2m_autocomplete_url(admin.site)
