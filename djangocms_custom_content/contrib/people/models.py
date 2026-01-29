from cms.models import CMSPlugin
from django.db import models
from django.utils.translation import gettext_lazy as _


class Person(models.Model):
    name = models.CharField(_("Name"), max_length=200)
    slug = models.SlugField(_("Slug"), unique=True)
    role = models.CharField(_("Role"), max_length=200, blank=True)
    bio = models.TextField(_("Bio"), blank=True)

    class Meta:
        verbose_name = _("Person")
        verbose_name_plural = _("People")
        ordering = ("name",)

    def __str__(self):
        return self.name


class PersonTeaser(CMSPlugin):
    person = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="plugins")
    show_bio = models.BooleanField(_("Show bio"), default=True)

    class Meta:
        verbose_name = _("Person teaser")
