from cms.models.fields import PlaceholderRelationField
from django.db import models


class AbstractCustomContent(models.Model):
    """
    Abstract base model providing a PlaceholderRelationField for custom content.

    Inherit from this model in your project to quickly add placeholder support
    to your custom content types.
    """

    placeholders = PlaceholderRelationField()

    class Meta:
        abstract = True
