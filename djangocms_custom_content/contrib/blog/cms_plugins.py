from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.utils.translation import gettext_lazy as _

from .models import BlogPostTeaser


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
