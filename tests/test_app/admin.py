"""Admin registration for test app models."""

from django.contrib import admin

from .models import RelTopic, SampleGrouper, SampleGrouperContent, StandaloneContent


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


@admin.register(RelTopic)
class RelTopicAdmin(admin.ModelAdmin):
    list_display = ("pk",)


@admin.register(StandaloneContent)
class StandaloneContentAdmin(admin.ModelAdmin):
    list_display = ("title",)
