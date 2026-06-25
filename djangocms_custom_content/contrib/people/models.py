from cms.models import CMSPlugin
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _
from filer.fields.image import FilerImageField

from djangocms_custom_content.models import AbstractCustomContent, AbstractCustomGrouper

User = get_user_model()


class Person(AbstractCustomGrouper):
    user = models.OneToOneField(User, null=True, blank=True, related_name="persons", on_delete=models.CASCADE)

    def __str__(self):
        if self.pk:
            return self.get_admin_content().name if self.get_admin_content() else str(self.pk)
        return "unsaved"


class PersonContent(AbstractCustomContent):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    slug = models.SlugField(_("slug"))
    name = models.CharField(_("name"), max_length=200, blank=False)
    role = models.CharField(_("role"), max_length=200, blank=True)
    description = models.TextField(_("description"), blank=True)
    phone = models.CharField(verbose_name=_("phone"), null=True, blank=True, max_length=100)
    mobile = models.CharField(verbose_name=_("mobile"), null=True, blank=True, max_length=100)
    fax = models.CharField(verbose_name=_("fax"), null=True, blank=True, max_length=100)
    email = models.EmailField(verbose_name=_("email"), blank=True, default="")
    website = models.URLField(verbose_name=_("website"), null=True, blank=True)
    visual = FilerImageField(null=True, blank=True, default=None, on_delete=models.SET_NULL)

    class Meta:
        verbose_name = _("Person")
        verbose_name_plural = _("People")
        ordering = ("name",)

    class CMSConfig:
        enable_versioning = True
        enable_frontend_editing = True
        apphook = True

    def __str__(self):
        return self.name


class PersonTeaser(CMSPlugin):
    person = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="plugins")
    show_bio = models.BooleanField(_("Show bio"), default=True)

    class Meta:
        verbose_name = _("Person teaser")
