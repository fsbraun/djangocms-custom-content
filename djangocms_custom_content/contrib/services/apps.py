from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ServicesConfig(AppConfig):
    name = "djangocms_custom_content.contrib.services"
    label = "djangocms_custom_content_services"
    verbose_name = _("Services")
    default_auto_field = "django.db.models.BigAutoField"
