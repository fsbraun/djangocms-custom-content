from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.utils.translation import gettext_lazy as _

from .models import CustomContent


@plugin_pool.register_plugin
class CustomContentPlugin(CMSPluginBase):
    model = CustomContent
    name = _("Custom Content")
    render_template = "djangocms_custom_content/default.html"
    cache = True
    allow_children = True

    fieldsets = [
        (
            None,
            {
                "fields": (
                    "template",
                    "content",
                )
            },
        ),
    ]

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        if instance.template:
            self.render_template = instance.template
        return context
