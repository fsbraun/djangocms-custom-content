from cms.models.fields import PlaceholderRelationField
from cms.models.managers import WithUserMixin
from django.db import models


class CustomGrouperMixin:
    pass


class AbstractCustomGrouper(CustomGrouperMixin, models.Model):
    class Meta:
        abstract = True

    def get_content(self, grouper_field_name: str):
        return self.personcontent_set(manager="admin_manager").latest_content().first()

    def get_admin_content(self): ...


class CustomContentManager(WithUserMixin, models.Manager):
    pass


class CustomContentMixin:
    pass


class AbstractCustomContent(CustomContentMixin, models.Model):
    """
    Abstract base model providing a PlaceholderRelationField for custom content.

    Inherit from this model in your project to quickly add placeholder support
    to your custom content types.
    """

    objects = CustomContentManager()
    placeholders = PlaceholderRelationField()

    class Meta:
        abstract = True
