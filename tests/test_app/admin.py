"""Admin registration for test app models."""

from django.contrib import admin

from djangocms_custom_content.admin import CustomM2MAdminMixin

from .models import (
    OtherTarget,
    RelTopic,
    SampleGrouper,
    SampleGrouperContent,
    StandaloneContent,
    TagTarget,
)


@admin.register(SampleGrouper)
class SampleGrouperAdmin(admin.ModelAdmin):
    """Admin for SampleGrouper model."""

    list_display = ("pk",)


@admin.register(SampleGrouperContent)
class SampleGrouperContentAdmin(admin.ModelAdmin):
    """Admin for SampleGrouperContent model."""

    list_display = ("title", "language", "grouper")
    list_filter = ("language",)
    search_fields = ("title",)


@admin.register(TagTarget)
class TagTargetAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(OtherTarget)
class OtherTargetAdmin(admin.ModelAdmin):
    list_display = ("label",)
    search_fields = ("label",)


@admin.register(RelTopic)
class RelTopicAdmin(CustomM2MAdminMixin, admin.ModelAdmin):
    list_display = ("pk",)
    m2m_sortable_fields = ["tags"]
    m2m_fields = ["featured", "hidden"]


@admin.register(StandaloneContent)
class StandaloneContentAdmin(CustomM2MAdminMixin, admin.ModelAdmin):
    list_display = ("title",)
    m2m_sortable_fields = ["targets"]
