from cms.admin.utils import GrouperModelAdmin
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from djangocms_custom_content.admin import CustomGrouperAdminMixin

from .models import Service, ServiceContent


@admin.register(Service)
class ServiceAdmin(CustomGrouperAdminMixin, GrouperModelAdmin):
    content_model = ServiceContent

    list_display = ("content__title", "content__is_featured")
    prepopulated_fields = {"content__slug": ("content__title",)}
    search_fields = ("content__title", "content__summary", "content__description")

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "content__title",
                    "content__slug",
                ),
            },
        ),
        (
            _("Description"),
            {
                "fields": (
                    "content__summary",
                    "content__description",
                    "content__is_featured",
                ),
            },
        ),
    )
