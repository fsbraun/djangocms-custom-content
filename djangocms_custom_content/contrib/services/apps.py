from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy as _


class ServicesConfig(AppConfig):
    name = "djangocms_custom_content.contrib.services"
    label = "djangocms_custom_content_services"
    verbose_name = _("Services")
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from .handlers import backfill_service_versions

        post_migrate.connect(backfill_service_versions, sender=self)
