from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.utils.translation import gettext_lazy as _

from .models import BlogPost, BlogPostTeaser, LatestBlogPosts


@plugin_pool.register_plugin
class BlogPostTeaserPlugin(CMSPluginBase):
    model = BlogPostTeaser
    name = _("Blog post")
    render_template = "djangocms_custom_content/contrib/blog/blog_post_teaser.html"
    cache = True
    allow_children = False

    fieldsets = [(None, {"fields": ("post",)})]

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context["post"] = instance.post
        return context


@plugin_pool.register_plugin
class LatestBlogPostsPlugin(CMSPluginBase):
    model = LatestBlogPosts
    name = _("Latest blog posts")
    render_template = "djangocms_custom_content/contrib/blog/latest_blog_posts.html"
    cache = True
    allow_children = False

    fieldsets = [(None, {"fields": ("category", "only_featured", "limit")})]

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        qs = BlogPost.objects.all()
        if instance.category_id:
            qs = qs.filter(categories=instance.category)
        if instance.only_featured:
            qs = qs.filter(is_featured=True)
        context["posts"] = list(qs[: instance.limit])
        return context
