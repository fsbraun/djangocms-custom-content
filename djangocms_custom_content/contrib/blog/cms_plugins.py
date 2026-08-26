from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.utils.translation import gettext_lazy as _

from .models import BlogPostList, BlogPostTeaser


@plugin_pool.register_plugin
class BlogPostTeaserPlugin(CMSPluginBase):
    model = BlogPostTeaser
    name = _("Blog post")
    render_template = "djangocms_custom_content_blog/blog_post_teaser.html"
    cache = True
    allow_children = False

    fieldsets = [(None, {"fields": ("post",)})]

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context["post"] = instance.post.get_content()
        return context


@plugin_pool.register_plugin
class BlogPostListPlugin(CMSPluginBase):
    """Paginated index of published posts, for the app hook's root page.

    The framework generates no list view on purpose, so that the root stays an
    editable CMS page. This plugin is the worked example of filling it.
    """

    model = BlogPostList
    name = _("Blog post list")
    render_template = "djangocms_custom_content_blog/blog_post_list.html"
    #: Output depends on the ``page-<pk>`` query parameter, so it must not be cached.
    cache = False
    allow_children = False

    fieldsets = [(None, {"fields": ("page_size", "only_featured")})]

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        posts = instance.get_queryset()

        if not instance.page_size:
            context["posts"] = posts
            context["page_obj"] = None
            return context

        paginator = Paginator(posts, instance.page_size)
        request = context.get("request")
        requested = request.GET.get(instance.page_kwarg) if request else None
        try:
            page = paginator.page(requested or 1)
        except PageNotAnInteger:
            page = paginator.page(1)
        except EmptyPage:
            # Out of range: show the last page rather than 404 inside a plugin.
            page = paginator.page(paginator.num_pages)

        context["posts"] = page.object_list
        context["page_obj"] = page
        context["paginator"] = paginator
        context["page_kwarg"] = instance.page_kwarg
        context["querystring"] = _querystring_without(request, instance.page_kwarg)
        return context


def _querystring_without(request, key: str) -> str:
    """The current query string minus ``key``, ready to prefix a page number.

    Keeps any other parameters (a filter, a tracking tag) across page links.
    """
    if request is None:
        return ""
    params = request.GET.copy()
    params.pop(key, None)
    encoded = params.urlencode()
    return f"{encoded}&" if encoded else ""
