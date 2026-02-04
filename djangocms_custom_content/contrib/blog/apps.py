from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class BlogConfig(AppConfig):
    name = "djangocms_custom_content.contrib.blog"
    label = "djangocms_custom_content_blog"
    verbose_name = _("Blog")
    default_auto_field = "django.db.models.BigAutoField"
