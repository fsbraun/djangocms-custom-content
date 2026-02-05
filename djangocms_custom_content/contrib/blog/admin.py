from cms.admin.placeholderadmin import FrontendEditableAdminMixin
from cms.admin.utils import GrouperModelAdmin
from django.contrib import admin

from djangocms_custom_content.admin import CustomGrouperAdminMixin

from .models import BlogPost


@admin.register(BlogPost)
class BlogPostAdmin(CustomGrouperAdminMixin, FrontendEditableAdminMixin, GrouperModelAdmin):
    grouper_field_name = "post"

    list_display = ("content__title", "content__published_at", "content__is_featured")
    # list_filter = ("content__is_featured", "content__published_at")
    prepopulated_fields = {"content__slug": ("content__title",)}
    search_fields = ("content__title", "content__excerpt", "content__body")

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        return form
