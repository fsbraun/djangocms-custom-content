from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.utils.translation import gettext_lazy as _

from .models import FeaturedServices, ServiceContent, ServiceTeaser


@plugin_pool.register_plugin
class ServiceTeaserPlugin(CMSPluginBase):
    model = ServiceTeaser
    name = _("Service")
    render_template = "djangocms_custom_content_services/service_teaser.html"
    cache = True
    allow_children = False

    fieldsets = [(None, {"fields": ("service",)})]

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        # ``instance.service`` is the grouper; the template renders its content.
        context["service"] = instance.service.get_content()
        return context


@plugin_pool.register_plugin
class FeaturedServicesPlugin(CMSPluginBase):
    model = FeaturedServices
    name = _("Featured services")
    render_template = "djangocms_custom_content_services/featured_services.html"
    cache = True
    allow_children = False

    fieldsets = [(None, {"fields": ("limit",)})]

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        # The default manager only yields published content when versioning is enabled.
        qs = ServiceContent.objects.filter(is_featured=True)
        context["services"] = list(qs[: instance.limit])
        return context
