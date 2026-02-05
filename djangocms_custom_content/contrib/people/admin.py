from cms.admin.utils import GrouperModelAdmin
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from djangocms_custom_content.admin import CustomGrouperAdminMixin

from .models import Person, PersonContent


@admin.register(Person)
class PersonAdmin(CustomGrouperAdminMixin, GrouperModelAdmin):
    content_model = PersonContent

    list_display = ("content__name", "content__visual", "content__role")
    prepopulated_fields = {"content__slug": ("content__name",)}
    search_fields = ("content__name", "content__role", "content__description")

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "content__name",
                    "content__slug",
                ),
            },
        ),
        (
            _("Description"),
            {
                "fields": (
                    "content__role",
                    "content__description",
                )
            },
        ),
        (
            _("Contact details"),
            {
                "fields": (
                    "content__visual",
                    (
                        "content__phone",
                        "content__mobile",
                    ),
                    ("content__email", "content__website"),
                    "user",
                ),
            },
        ),
    )
