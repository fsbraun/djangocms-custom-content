from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PeopleConfig(AppConfig):
    name = "djangocms_custom_content.contrib.people"
    label = "djangocms_custom_content_people"
    verbose_name = _("Custom Content - People (Example)")
    default_auto_field = "django.db.models.BigAutoField"
