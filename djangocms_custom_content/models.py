from collections.abc import Callable

from cms.models.fields import PlaceholderRelationField
from cms.models.managers import WithUserMixin
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.base import ModelBase
from django.db.models.fields.reverse_related import ForeignObjectRel
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from djangocms_custom_content.helpers import get_custom_config


class CustomGrouperMixin:
    pass


class AbstractCustomGrouper(CustomGrouperMixin, models.Model):
    class Meta:
        abstract = True

    _content_set = None
    _has_language_field = False
    _content_cache: models.Model | dict[str, models.Model] | None = None
    _is_admin_cache = None

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
                self._content_cache = {obj.language: obj for obj in qs}
            return self._content_cache.get(language)

        if self._content_cache is None:
            self._content_cache = qs.first()
        return self._content_cache

    def get_content(self, language: str | None = None) -> models.Model | None:
        if self._is_admin_cache:
            self._is_admin_cache = False
            self._content_cache = None
        return self._get_content(language or get_language(), self._content_set)

    def get_admin_content(self, language: str | None = None) -> models.Model | None:
        if hasattr(self, "_admin_prefetch_cache") and not self._is_admin_cache:
            if self._has_language_field is None:
                self._content_cache = {obj.language: obj for obj in self._admin_prefetch_cache}
            else:
                self._content_cache = self._admin_prefetch_cache[0]
        self._is_admin_cache = True
        return self._get_content(
            language or get_language(), self._content_set(manager="admin_manager").latest_content()
        )


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


class AbstractCustomRelation(models.Model):
    """
    Abstract base model to define the relation between a custom grouper and content.

    This model should be used when the relation between the grouper and content
    models is not a simple ForeignKey, for example when using a ManyToManyField
    or when additional fields are needed on the relation.
    """

    class Meta:
        abstract = True

    # Generic foreign key to any model
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_("content type"),
    )
    object_id = models.PositiveIntegerField(
        _("object id"),
    )
    content_object = GenericForeignKey("content_type", "object_id")

    instance = None  # This will be set to the related grouper instance when the relation is accessed

    def __str__(self) -> str:
        return f"{self.instance} -> {self.content_object}"


class _InverseRelationManager:
    def __init__(self, instance, relation_model):
        self.instance = instance
        self.relation_model = relation_model

    def add(self, obj):
        ct = ContentType.objects.get_for_model(obj)
        self.relation_model.objects.get_or_create(
            instance=self.instance,
            content_type=ct,
            object_id=obj.pk,
        )

    def remove(self, obj):
        ct = ContentType.objects.get_for_model(obj)
        self.relation_model.objects.filter(
            instance=self.instance,
            content_type=ct,
            object_id=obj.pk,
        ).delete()

    def all(self):
        return [
            rel.content_object
            for rel in self.relation_model.objects.filter(instance=self.instance).select_related("content_type")
        ]


class InverseRelationDescriptor:
    def __init__(self, relation_model: type[models.Model]):
        self.relation_model = relation_model

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return _InverseRelationManager(instance, self.relation_model)


class GenericM2MManager:
    def __init__(self, instance: models.Model, through_model: type[AbstractCustomRelation], related_field_name: str):
        self.instance = instance
        self.through_model = through_model
        self.related_field_name = related_field_name
        self.content_type = ContentType.objects.get_for_model(instance)

    def get_queryset(self):
        return self.through_model.objects.filter(content_type=self.content_type, object_id=self.instance.pk)

    def all(self):
        return self._related_queryset()

    def add(self, *objs):
        for obj in objs:
            self.through_model.objects.get_or_create(
                **{
                    self.related_field_name: obj,
                    "content_type": self.content_type,
                    "object_id": self.instance.pk,
                }
            )

    def remove(self, *objs):
        self.get_queryset().filter(**{f"{self.related_field_name}__in": objs}).delete()

    def clear(self):
        self.get_queryset().delete()

    def _related_queryset(self):
        return self.through_model._meta.get_field("instance").related_model.admin_manager.filter(
            pk__in=self.through_model.objects.filter(
                content_type=self.content_type, object_id=self.instance.pk
            ).values_list(self.related_field_name, flat=False)
        )


class GenericM2MDescriptor:
    def __init__(self, relation_model: type[models.Model], related_field_name: str):
        self.relation_model = relation_model
        self.related_field_name = related_field_name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return GenericM2MManager(instance, self.relation_model, self.related_field_name)


def custom_relation_factory(model: type[models.Model], related_name: str | None = None) -> type[models.Model]:
    relation_model = ModelBase(
        f"{model.__name__}Relation",
        (AbstractCustomRelation,),
        {
            "instance": models.ForeignKey(
                model,
                on_delete=models.CASCADE,
                related_name="+",
            ),
            "__module__": model.__module__,
        },
    )
    if related_name is None:
        related_name = "relation_set"

    model.add_to_class(related_name, InverseRelationDescriptor(relation_model))  # type: ignore
    return relation_model  # type: ignore
