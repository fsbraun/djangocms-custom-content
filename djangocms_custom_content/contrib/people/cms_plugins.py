from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.utils.translation import gettext_lazy as _

from .models import PersonTeaser


@plugin_pool.register_plugin
class PersonTeaserPlugin(CMSPluginBase):
    model = PersonTeaser
    name = _("Person")
    render_template = "people/person_teaser.html"
    allow_children = False
    grouper_field = "person"

    fieldsets = [(None, {"fields": ("person", "show_bio")})]

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context["person_content"] = instance.person.get_content(self.grouper_field)
        return context
