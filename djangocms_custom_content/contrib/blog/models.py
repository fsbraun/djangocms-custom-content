from cms.models import CMSPlugin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from djangocms_custom_content.models import AbstractCustomContent, AbstractCustomGrouper


class BlogPost(AbstractCustomGrouper):
    pass


class BlogPostContent(AbstractCustomContent):
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE)
    title = models.CharField(_("Title"), max_length=200)
    slug = models.SlugField(_("Slug"))  # Uniquness not enforced here to allow multple languages and versions
    excerpt = models.TextField(_("Excerpt"), blank=True)
    body = models.TextField(_("Body"), blank=True)
    published_at = models.DateTimeField(_("Published at"), default=timezone.now)
    is_featured = models.BooleanField(_("Featured"), default=False)
    language = models.CharField(_("Language"), max_length=8)

    class Meta:
        verbose_name = _("Blog post")
        verbose_name_plural = _("Blog posts")
        ordering = ("-published_at",)

    class CMSConfig:
        enable_versioning = True
        enable_frontend_editing = True
        m2m = [
            ("authors", "djangocms_custom_content_people.Person"),
            ("categories", "djangocms_custom_content_categories.FlatCategory"),
        ]

    def get_template(self):
        return "blog/detail.html"

    def __str__(self):
        return self.title


class BlogPostTeaser(CMSPlugin):
    post = models.ForeignKey(BlogPost, on_delete=models.PROTECT, related_name="plugins")

    class Meta:
        verbose_name = _("Blog post teaser")
