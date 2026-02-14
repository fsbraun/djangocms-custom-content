# Test models
from django.contrib.contenttypes.models import ContentType
from django.db import models

from djangocms_custom_content.models import (
    AbstractCustomContent,
    AbstractCustomGrouper,
    AbstractCustomRelation,
)


class Author(models.Model):
    """Simple model to use as a grouper for testing custom relations."""

    name = models.CharField(max_length=100)

    class Meta:
        app_label = "test_app"

    def __str__(self):
        return self.name


class Book(models.Model):
    """Simple model to use as content for testing generic relations."""

    title = models.CharField(max_length=200)
    author = models.CharField(max_length=100)

    class Meta:
        app_label = "test_app"

    def __str__(self):
        return self.title


class Article(models.Model):
    """Another content model for testing."""

    headline = models.CharField(max_length=200)

    class Meta:
        app_label = "test_app"

    def __str__(self):
        return self.headline


class AuthorRelation(AbstractCustomRelation):
    """Relation model for testing GenericM2M relations."""

    instance = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="+")

    class Meta:
        app_label = "test_app"


class BookRelation(AbstractCustomRelation):
    """Relation model for testing GenericM2M relations with Book."""

    instance = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="+")

    class Meta:
        app_label = "test_app"

    def __str__(self):
        return self.headline


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
