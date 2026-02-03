from cms.models import CMSPlugin
from django.db import models
from django.utils.translation import gettext_lazy as _

from djangocms_custom_content.models import AbstractCustomContent, AbstractCustomGrouper


class PersonGrouper(AbstractCustomGrouper):
    slug = models.SlugField(_("Slug"), unique=True)


class Person(AbstractCustomContent):
    name = models.CharField(_("Name"), max_length=200)
    role = models.CharField(_("Role"), max_length=200, blank=True)
    bio = models.TextField(_("Bio"), blank=True)
    person_grouper = models.ForeignKey(PersonGrouper, on_delete=models.CASCADE)

    class Meta:
        verbose_name = _("Person")
        verbose_name_plural = _("People")
        ordering = ("name",)

    class CMSConfig:
        enable_versioning = True
        enable_frontend_editing = True

    def get_template(self):
        return "people/detail.html"

    def __str__(self):
        return self.name


class PersonTeaser(CMSPlugin):
    person = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="plugins")
    show_bio = models.BooleanField(_("Show bio"), default=True)

    class Meta:
        verbose_name = _("Person teaser")
