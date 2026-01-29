from cms.models import CMSPlugin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from ..categories.models import Category


class BlogPost(models.Model):
    title = models.CharField(_("Title"), max_length=200)
    slug = models.SlugField(_("Slug"), unique=True)
    excerpt = models.TextField(_("Excerpt"), blank=True)
    body = models.TextField(_("Body"), blank=True)
    published_at = models.DateTimeField(_("Published at"), default=timezone.now)
    is_featured = models.BooleanField(_("Featured"), default=False)

    categories = models.ManyToManyField(Category, blank=True, related_name="blog_posts")

    class Meta:
        verbose_name = _("Blog post")
        verbose_name_plural = _("Blog posts")
        ordering = ("-published_at",)

    def __str__(self):
        return self.title


class BlogPostTeaser(CMSPlugin):
    post = models.ForeignKey(BlogPost, on_delete=models.PROTECT, related_name="plugins")

    class Meta:
        verbose_name = _("Blog post teaser")


class LatestBlogPosts(CMSPlugin):
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    limit = models.PositiveIntegerField(_("Limit"), default=5)
    only_featured = models.BooleanField(_("Only featured"), default=False)

    class Meta:
        verbose_name = _("Latest blog posts")
