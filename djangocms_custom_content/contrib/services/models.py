from cms.models import CMSPlugin
from django.db import models
from django.utils.translation import gettext_lazy as _


class Service(models.Model):
    title = models.CharField(_("Title"), max_length=200)
    slug = models.SlugField(_("Slug"), unique=True)
    summary = models.TextField(_("Summary"), blank=True)
    description = models.TextField(_("Description"), blank=True)
    is_featured = models.BooleanField(_("Featured"), default=False)

    class Meta:
        verbose_name = _("Service")
        verbose_name_plural = _("Services")
        ordering = ("title",)

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
