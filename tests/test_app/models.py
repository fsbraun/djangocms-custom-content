# Test models
from django.db import models

from djangocms_custom_content.models import AbstractCustomContent, AbstractCustomGrouper


class TagTarget(models.Model):
    """Plain Django model used as the target of m2m relations in tests."""

    name = models.CharField(max_length=100)

    class Meta:
        app_label = "test_app"

    def __str__(self):
        return self.name


class OtherTarget(models.Model):
    """Second plain target, used to verify multiple relations to the same model class."""

    label = models.CharField(max_length=100)

    class Meta:
        app_label = "test_app"

    def __str__(self):
        return self.label


class RelTopic(AbstractCustomGrouper):
    """Grouper for testing CMSConfig.m2m on its content model."""

    class Meta:
        app_label = "test_app"

    def __str__(self):
        return f"RelTopic {self.pk}"


class RelTopicContent(AbstractCustomContent):
    """Content model declaring m2m relations for tests."""

    topic = models.ForeignKey(RelTopic, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    language = models.CharField(max_length=5, default="en")

    class Meta:
        app_label = "test_app"

    class CMSConfig:
        m2m = [
            ("tags", "test_app.TagTarget"),                       # auto reverse: reltopic_set
            ("featured", "test_app.TagTarget", "featured_in"),    # explicit reverse name
            ("hidden", "test_app.OtherTarget", None),             # no reverse accessor
        ]

    def __str__(self):
        return self.title


class StandaloneContent(AbstractCustomContent):
    """Content model with no grouper — relation FK should point to itself."""

    title = models.CharField(max_length=200)

    class Meta:
        app_label = "test_app"

    class CMSConfig:
        m2m = [
            ("targets", "test_app.TagTarget"),
        ]

    def __str__(self):
        return self.title


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
