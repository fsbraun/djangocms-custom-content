from cms.models import CMSPlugin
from django.db import models
from django.utils.translation import gettext_lazy as _

from djangocms_custom_content.models import AbstractCustomContent, AbstractCustomGrouper


class Service(AbstractCustomGrouper):
    """Groups the versions of a service.

    The grouper carries no fields of its own: it is the stable identity that plugins
    point at, so a version copy never invalidates a plugin's foreign key.
    """

    def __str__(self):
        if self.pk:
            content = self.get_admin_content()
            return content.title if content else str(self.pk)
        return "unsaved"


class ServiceContent(AbstractCustomContent):
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    title = models.CharField(_("Title"), max_length=200)
    slug = models.SlugField(_("Slug"))  # Not unique: versions of one service share a slug
    summary = models.TextField(_("Summary"), blank=True)
    description = models.TextField(_("Description"), blank=True)
    is_featured = models.BooleanField(_("Featured"), default=False)

    class Meta:
        verbose_name = _("Service")
        verbose_name_plural = _("Services")
        ordering = ("title",)

    class CMSConfig:
        enable_versioning = True
        enable_frontend_editing = True
        admin_menu = True

    def __str__(self):
        return self.title


class ServiceTeaser(CMSPlugin):
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="plugins")

    class Meta:
        verbose_name = _("Service teaser")


class FeaturedServices(CMSPlugin):
    limit = models.PositiveIntegerField(_("Limit"), default=3)

    class Meta:
        verbose_name = _("Featured services")
