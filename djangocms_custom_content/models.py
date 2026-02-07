from collections.abc import Callable

from cms.models.fields import PlaceholderRelationField
from cms.models.managers import WithUserMixin
from django.db import models
from django.db.models.fields.reverse_related import ForeignObjectRel
from django.utils.translation import get_language

from djangocms_custom_content.helpers import get_custom_config


class CustomGrouperMixin:
    pass


class AbstractCustomGrouper(CustomGrouperMixin, models.Model):
    class Meta:
        abstract = True

    _content_set = None
    _has_language_field = False
    _content_cache: models.Model | dict[str, models.Model] | None = None
    _admin_cache = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self._content_set is None:
            # Identify the reverse relation for the custom content model
            for field in self._meta.get_fields():
                if isinstance(field, ForeignObjectRel) and issubclass(field.related_model, CustomContentMixin):
                    accessor = field.get_accessor_name()
                    if accessor:
                        self._content_set = getattr(self, accessor)
                        self.__class__._content_set = self._content_set
                        self._custom_model = field.related_model
                        config = get_custom_config(self._custom_model)
                        self._grouper_field_name = config[1]
                        self._has_language_field = config[2]
                        self.__class__._has_language_field = config[2]
                        break

    def _get_content(self, language: str, qs) -> models.Model | None:
        if self._content_set is None:
            # No content model found related to this grouper, return None
            return None

        if self._has_language_field:
            if self._content_cache is None:
                if hasattr(self, "_content_prefetch_cache"):
                    self._content_cache = {obj.language: obj for obj in self._content_prefetch_cache}
                else:
                    self._content_cache = {obj.language: obj for obj in qs}
            return self._content_cache.get(language)

        if self._content_cache is None:
            if hasattr(self, "_content_prefetch_cache"):
                self._content_cache = self._content_prefetch_cache[0]
            else:
                self._content_cache = qs.first()
        return self._content_cache

    def get_content(self, language: str | None = None) -> models.Model | None:
        return self._get_content(language or get_language(), self._content_set)

    def get_admin_content(self, language: str | None = None) -> models.Model | None:
        return self._get_content(
            language or get_language(), self._content_set(manager="admin_manager").latest_content()
        )

    @classmethod
    def resolve_content(cls, **kwargs) -> models.Model | None:
        """Resolves the content for this grouper, only serving public content if available."""
        if cls._content_set is None:
            return None

        if cls._has_language_field:
            language = kwargs.get("language") or get_language()
            return cls._content_set.filter(language=language, **kwargs).first()
        return cls._content_set.filter(**kwargs).first()


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

    template_name_suffix = "_detail"

    class Meta:
        abstract = True

    def get_template(self) -> str:
        object_meta = self._meta
        return "{}/{}{}.html".format(
            object_meta.app_label,
            object_meta.model_name,
            self.template_name_suffix,
        )
