from cms.models import CMSPlugin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from djangocms_custom_content.models import AbstractCustomContent, AbstractCustomGrouper
from djangocms_custom_content.relations import RelationField


class BlogPost(AbstractCustomGrouper):
    # Grouper-anchored relations: survive version copies, read like M2M.
    # The forward accessor lives on the post; the ``related_name`` is the
    # reverse accessor invited onto the target without it declaring anything.
    authors = RelationField(
        "djangocms_custom_content_people.Person",
        related_name="authored_posts",
        ordered=True,
    )
    categories = RelationField(
        "djangocms_custom_content_categories.FlatCategory",
        related_name="blog_posts",
    )


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
        admin_menu = True

    def __str__(self):
        return self.title


class BlogPostTeaser(CMSPlugin):
    post = models.ForeignKey(BlogPost, on_delete=models.PROTECT, related_name="plugins")

    class Meta:
        verbose_name = _("Blog post teaser")


class BlogPostList(CMSPlugin):
    """A paginated index of published posts.

    The app hook generates no list view, so the page it is attached to stays an
    ordinary CMS page and this plugin builds the index on it -- alongside whatever
    else an editor wants there. It works on any page, not only the app hook root.
    """

    page_size = models.PositiveIntegerField(
        _("Posts per page"),
        default=10,
        help_text=_("0 shows every post on one page."),
    )
    only_featured = models.BooleanField(_("Only featured"), default=False)

    class Meta:
        verbose_name = _("Blog post list")
        verbose_name_plural = _("Blog post lists")

    def __str__(self):
        return str(self._meta.verbose_name)

    @property
    def page_kwarg(self) -> str:
        """Query parameter holding the page number.

        Namespaced by primary key so two list plugins on one page paginate
        independently.
        """
        return f"page-{self.pk}" if self.pk else "page"

    def get_queryset(self) -> models.QuerySet:
        """Published posts, newest first (the model's own ordering)."""
        queryset = BlogPostContent.objects.all()
        if self.only_featured:
            queryset = queryset.filter(is_featured=True)
        return queryset
