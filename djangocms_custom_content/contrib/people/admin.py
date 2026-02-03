from cms.admin.utils import GrouperModelAdmin
from django.contrib import admin

from djangocms_custom_content.admin import CustomGrouperAdminMixin

from .models import Person, PersonGrouper


@admin.register(PersonGrouper)
class PersonAdmin(CustomGrouperAdminMixin, GrouperModelAdmin):
    content_model = Person
    grouper_field_name = "person_grouper"

    list_display = ("content__name", "content__role")
    prepopulated_fields = {"slug": ("content__name",)}
    search_fields = ("content__name", "content__role", "content__bio")
