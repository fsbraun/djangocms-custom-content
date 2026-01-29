from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CustomContentConfig(AppConfig):
    name = "djangocms_custom_content"
    verbose_name = _("django CMS Custom Content")
    default_auto_field = "django.db.models.BigAutoField"
