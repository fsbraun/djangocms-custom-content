from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CategoriesConfig(AppConfig):
    name = "djangocms_custom_content.contrib.categories"
    label = "djangocms_custom_content_categories"
    verbose_name = _("Global categories")
    default_auto_field = "django.db.models.BigAutoField"
