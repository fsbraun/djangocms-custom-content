from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.utils.translation import gettext_lazy as _

from .models import FeaturedServices, Service, ServiceTeaser


@plugin_pool.register_plugin
class ServiceTeaserPlugin(CMSPluginBase):
    model = ServiceTeaser
    name = _("Service")
    render_template = "djangocms_custom_content/contrib/services/service_teaser.html"
    cache = True
    allow_children = False

    fieldsets = [(None, {"fields": ("service",)})]

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context["service"] = instance.service
        return context


@plugin_pool.register_plugin
class FeaturedServicesPlugin(CMSPluginBase):
    model = FeaturedServices
    name = _("Featured services")
    render_template = "djangocms_custom_content/contrib/services/featured_services.html"
    cache = True
    allow_children = False

    fieldsets = [(None, {"fields": ("limit",)})]

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        qs = Service.objects.filter(is_featured=True)
        context["services"] = list(qs[: instance.limit])
        return context
