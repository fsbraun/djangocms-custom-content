from cms.models import CMSPlugin
from django.db import models
from django.utils.translation import gettext_lazy as _

from djangocms_custom_content.models import AbstractCustomContent


class FlatCategory(AbstractCustomContent):
    title = models.CharField(_("Title"), max_length=100)
    slug = models.SlugField(_("Slug"), unique=True)
    is_featured = models.BooleanField(_("Featured"), default=False)

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ("title",)

    def __str__(self):
        return self.title


class FlatCategoryList(CMSPlugin):
    only_featured = models.BooleanField(_("Only featured"), default=False)
    limit = models.PositiveIntegerField(_("Limit"), default=0, help_text=_("0 = no limit"))

    class Meta:
        verbose_name = _("Category list")
