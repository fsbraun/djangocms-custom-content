from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.utils.translation import gettext_lazy as _

from .models import Category, CategoryList


@plugin_pool.register_plugin
class CategoryListPlugin(CMSPluginBase):
    model = CategoryList
    name = _("Categories")
    render_template = "djangocms_custom_content/contrib/categories/category_list.html"
    cache = True
    allow_children = False

    fieldsets = [(None, {"fields": ("only_featured", "limit")})]

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        qs = Category.objects.all()
        if instance.only_featured:
            qs = qs.filter(is_featured=True)
        if instance.limit:
            qs = qs[: instance.limit]
        context["categories"] = list(qs)
        return context
