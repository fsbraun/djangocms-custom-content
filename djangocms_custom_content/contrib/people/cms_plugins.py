from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.utils.translation import gettext_lazy as _

from .models import PersonTeaser


@plugin_pool.register_plugin
class PersonTeaserPlugin(CMSPluginBase):
    model = PersonTeaser
    name = _("Person")
    render_template = "djangocms_custom_content/contrib/people/person_teaser.html"
    cache = True
    allow_children = False

    fieldsets = [(None, {"fields": ("person", "show_bio")})]

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context["person"] = instance.person
        return context
