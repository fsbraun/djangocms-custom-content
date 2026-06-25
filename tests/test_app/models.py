# Test models
from django.db import models

from djangocms_custom_content.models import (
    AbstractCustomContent,
    AbstractCustomGrouper,
)


class SampleGrouper(AbstractCustomGrouper):
    """Sample grouper model for testing AbstractCustomGrouper functionality."""

    class Meta:
        app_label = "test_app"

    def __str__(self):
        return f"SampleGrouper {self.pk}"


class SampleGrouperContent(AbstractCustomContent):
    """Sample content model for testing AbstractCustomGrouper get_content and caching."""

    grouper = models.ForeignKey(SampleGrouper, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    language = models.CharField(max_length=5, default="en")
    body = models.TextField(blank=True)

    class Meta:
        app_label = "test_app"

    def __str__(self):
        return f"{self.title} ({self.language})"
