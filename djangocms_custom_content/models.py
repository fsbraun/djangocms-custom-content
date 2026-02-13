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
    """
    Mixin providing base grouper functionality.

    This mixin is inherited by :class:`AbstractCustomGrouper` to provide
    grouper model functionality. It serves as a marker class for identifying
    grouper models in the framework.
    """

    pass


class AbstractCustomGrouper(CustomGrouperMixin, models.Model):
    """
    Abstract base model for grouper objects.

    A grouper is a container that organizes multiple language versions of content.
    Inherit from this model when you want to group content versions together.

    The grouper automatically discovers its related content model and provides
    methods to access content by language.

    Example::

        class Article(AbstractCustomGrouper):
            '''Groups all language versions of an article.'''
            pass

        class ArticleContent(AbstractCustomContent):
            article = ForeignKey(Article, on_delete=CASCADE)
            title = CharField(max_length=200)
            language = CharField(max_length=5)

    Attributes:
        _content_set: Cache for the related content model manager
        _has_language_field: Whether the content model has a language field
        _content_cache: Cache for retrieved content instances
        _is_admin_cache: Flag for admin-specific caching
    """

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
        """
        Internal method to retrieve content by language.

        Implements caching logic for efficient content retrieval.

        Args:
            ``language``: The language code to retrieve content for
            ``qs``: The queryset to retrieve from

        Returns:
            The content model instance or None if not found
        """
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
        """
        Retrieve content for this grouper in a specific language.

        Uses the current language by default if no language is specified.
        Implements caching for performance.

        Args:
            ``language``: The language code to retrieve. Defaults to current language.

        Returns:
            The content model instance for the specified language, or None if not found

        Example::

            article = Article.objects.first()
            english_content = article.get_content(language='en')
            german_content = article.get_content(language='de')
        """
        if self._is_admin_cache:
            self._is_admin_cache = False
            self._content_cache = None
        return self._get_content(language or get_language(), self._content_set)

    def get_admin_content(self, language: str | None = None) -> models.Model | None:
        """
        Retrieve content for admin interface with prefetch optimization.

        This method is optimized for admin display and uses prefetched data
        when available. It retrieves the latest published content.

        Args:
            ``language``: The language code to retrieve. Defaults to current language.

        Returns:
            The latest content model instance for the specified language, or None if not found

        Notes:
            This method is primarily used by the Django admin interface.
        """
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
    """
    Manager for custom content models.

    Provides Django CMS user tracking functionality via :class:`WithUserMixin`,
    allowing automatic tracking of which user created or modified content.
    """

    pass


class CustomContentMixin:
    """
    Mixin providing base content model functionality.

    This mixin is inherited by :class:`AbstractCustomContent` to provide
    content model functionality. It serves as a marker class for identifying
    content models in the framework.
    """

    pass


class AbstractCustomContent(CustomContentMixin, models.Model):
    """
    Abstract base model providing a PlaceholderRelationField for custom content.

    Inherit from this model in your project to quickly add placeholder support
    to your custom content types.

    To define generic many-to-many relationships with other models, create a
    CMSConfig class with the ``m2m_relations`` attribute:

        class MyContentModel(AbstractCustomContent):
            # ... fields ...

            class CMSConfig:
                m2m_relations = [("related_set", "app_label.RelatedModel")]

        # Create the relation model (required):
        MyContentRelation = custom_relation_factory(MyContentModel)

    See the documentation for more details on m2m_relations.
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
    Abstract base model for storing generic many-to-many relations.

    This model implements a generic foreign key pattern, allowing your content
    models to be related to any Django model without explicitly defining foreign keys.

    The relation is stored using Django's :class:`~django.contrib.contenttypes.models.ContentType`
    framework, which enables flexible relationships to any model.

    Useful for:

    - Creating flexible M2M relationships to multiple model types
    - Avoiding explicit ForeignKey definitions when relations are dynamic
    - Implementing patterns like "related items" or "linked content"

    Attributes:
        instance: ForeignKey to the content model (set via :func:`custom_relation_factory`)
        content_type: ForeignKey to ContentType identifying the related model
        object_id: ID of the related object
        content_object: GenericForeignKey providing access to the actual related object

    Example::

        # This is created automatically via custom_relation_factory:
        class PersonRelation(AbstractCustomRelation):
            instance = ForeignKey(PersonContent, on_delete=CASCADE)

        # Use via the descriptor on related models:
        blog_post = BlogPost.objects.first()
        blog_post.authors.all()  # Returns all related PersonContent objects

    See Also:
        :func:`custom_relation_factory` - Factory to create relation models
        :class:`GenericM2MManager` - Manager providing the relation interface
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
    """
    Internal manager for accessing inverse relations via descriptors.

    This class is used internally by :class:`InverseRelationDescriptor` to provide
    a manager interface for accessing related objects. It handles getting, adding,
    and removing relations through the relation model.

    This should not be instantiated directly; it is created automatically by
    descriptors.

    Args:
        ``instance``: The model instance this manager is bound to
        ``relation_model``: The relation model (inherits from :class:`AbstractCustomRelation`)
    """

    def __init__(self, instance, relation_model):
        self.instance = instance
        self.relation_model = relation_model

    def add(self, obj):
        """Add a related object to this instance's relations.

        Args:
            ``obj``: The object to relate to this instance
        """
        ct = ContentType.objects.get_for_model(obj)
        self.relation_model.objects.get_or_create(
            instance=self.instance,
            content_type=ct,
            object_id=obj.pk,
        )

    def remove(self, obj):
        """Remove a related object from this instance's relations.

        Args:
            ``obj``: The object to remove from this instance's relations
        """
        ct = ContentType.objects.get_for_model(obj)
        self.relation_model.objects.filter(
            instance=self.instance,
            content_type=ct,
            object_id=obj.pk,
        ).delete()

    def all(self):
        """Return all related objects for this instance.

        Returns:
            list: A list of all related objects
        """
        return [
            rel.content_object
            for rel in self.relation_model.objects.filter(instance=self.instance).select_related("content_type")
        ]


class InverseRelationDescriptor:
    """
    Descriptor providing access to inverse generic M2M relations.

    This descriptor is assigned to models to provide a manager interface for
    accessing models that are related via :class:`AbstractCustomRelation`.

    The descriptor returns itself when accessed on the class, and returns a
    :class:`_InverseRelationManager` instance when accessed on a model instance.

    Args:
        ``relation_model``: The relation model (inherits from :class:`AbstractCustomRelation`)

    Example::

        instance = MyModel.objects.first()
        # Access all related objects
        manager = instance.related_set  # Returns _InverseRelationManager
        all_related = manager.all()
    """

    def __init__(self, relation_model: type[models.Model]):
        self.relation_model = relation_model

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return _InverseRelationManager(instance, self.relation_model)


class GenericM2MManager:
    """
    Manager for generic many-to-many relationships using ContentType framework.

    This manager provides a simple interface for managing relationships between
    a model instance and related objects of any type, stored in a custom relation
    model that inherits from AbstractCustomRelation.

    Usage:
        Instance managers are created automatically via GenericM2MDescriptor and
        should not be instantiated directly.

    Example::

        # After defining m2m_relations in CMSConfig:
        blog_post = BlogPost.objects.first()
        authors = blog_post.author_set.all()  # Returns all related PersonContent objects
        blog_post.author_set.add(person_content)  # Add a relation
        blog_post.author_set.remove(person_content)  # Remove a relation
    """

    def __init__(self, instance: models.Model, through_model: type[AbstractCustomRelation], related_field_name: str):
        """Initialize the manager.

        Args:
            ``instance``: The model instance this manager is bound to
            ``through_model``: The relation model (inherits from AbstractCustomRelation)
            ``related_field_name``: The field name on the through_model pointing to related objects
        """
        self.instance = instance
        self.through_model = through_model
        self.related_field_name = related_field_name
        self.content_type = ContentType.objects.get_for_model(instance)

    def get_queryset(self):
        """Return the queryset of relation objects for this instance."""
        return self.through_model.objects.filter(content_type=self.content_type, object_id=self.instance.pk)

    def all(self):
        """Return all related objects."""
        return self._related_queryset()

    def add(self, *objs):
        """Add one or more objects to the relation.

        Uses get_or_create to prevent duplicates.

        Args:
            ``*objs``: One or more model instances to add
        """
        for obj in objs:
            self.through_model.objects.get_or_create(
                **{
                    self.related_field_name: obj,
                    "content_type": self.content_type,
                    "object_id": self.instance.pk,
                }
            )

    def remove(self, *objs):
        """Remove one or more objects from the relation.

        Args:
            ``*objs``: One or more model instances to remove
        """
        self.get_queryset().filter(**{f"{self.related_field_name}__in": objs}).delete()

    def clear(self):
        """Remove all relations for this instance."""
        self.get_queryset().delete()

    def _related_queryset(self):
        """Return a queryset of the actual related objects (not relations)."""
        related_model = self.through_model._meta.get_field("instance").related_model
        # Use admin_manager if available (for versioned content models), otherwise use objects
        manager = getattr(related_model, "admin_manager", None) or related_model.objects
        return manager.filter(
            pk__in=self.through_model.objects.filter(
                content_type=self.content_type, object_id=self.instance.pk
            ).values_list(self.related_field_name, flat=False)
        )


class GenericM2MDescriptor:
    """
    Descriptor that provides a GenericM2MManager for generic M2M relationships.

    This descriptor is automatically assigned to models via m2m_relations
    in CMSConfig and provides the manager interface for accessing relationships.

    The descriptor returns itself when accessed on the class, and returns a
    GenericM2MManager instance when accessed on a model instance.
    """

    def __init__(self, relation_model: type[models.Model], related_field_name: str):
        """Initialize the descriptor.

        Args:
            ``relation_model``: The relation model (inherits from AbstractCustomRelation)
            ``related_field_name``: The field name on the relation model pointing to related objects
        """
        self.relation_model = relation_model
        self.related_field_name = related_field_name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return GenericM2MManager(instance, self.relation_model, self.related_field_name)


class DummyM2MManager:
    """
    Dummy manager for simulating empty generic M2M relationships.

    This manager provides a no-op interface that simulates an empty relationship,
    used when a related model is not available or does not exist.

    All operations are no-ops and queries return empty results.
    """

    def __init__(self, instance: models.Model, accessor: str):
        """Initialize the dummy manager.

        Args:
            ``instance``: The model instance this manager is bound to
            ``accessor``: The name of the accessor attribute
        """
        self.instance = instance
        self.accessor = accessor

    def all(self):
        """Return an empty list (no relations exist)."""
        return []

    def add(self, *objs):
        """No-op: does nothing."""
        pass

    def remove(self, *objs):
        """No-op: does nothing."""
        pass

    def clear(self):
        """No-op: does nothing."""
        pass


class DummyM2MDescriptor:
    """
    Descriptor providing a dummy interface for unavailable generic M2M relations.

    This descriptor is used when a related model specified in m2m_relations
    cannot be found or is not yet available. It provides a safe interface that
    returns empty results instead of raising errors.

    The descriptor returns itself when accessed on the class, and returns a
    DummyM2MManager instance when accessed on a model instance.
    """

    def __init__(self, accessor: str):
        """Initialize the descriptor.

        Args:
            ``accessor``: The name of the accessor attribute
        """
        self.accessor = accessor

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return DummyM2MManager(instance, self.accessor)


def custom_relation_factory(model: type[models.Model], related_name: str | None = None) -> type[models.Model]:
    """
    Factory function to create a relation model for use with m2m_relations.

    This function creates a concrete relation model that inherits from
    AbstractCustomRelation and is linked to the provided model. The relation model
    is required when using m2m_relations in a model's CMSConfig.

    :param model: The content model to create a relation model for.
    :param related_name: Optional. The name of the reverse accessor on the model.
        Defaults to ``relation_set``.
    :returns: A new relation model class that can be used with ``m2m_relations``.

    Example:

    .. code-block:: python

        from djangocms_custom_content.models import AbstractCustomContent, custom_relation_factory

        class PersonContent(AbstractCustomContent):
            # ... fields ...

            class CMSConfig:
                m2m_relations = [("author_set", "blog.BlogPost")]

                # Create the relation model (required for m2m_relations)
                PersonRelation = custom_relation_factory(PersonContent)

    Notes:
            - This must be called at the module level to ensure proper registration.
            - The returned model class will have an ``instance`` ForeignKey to the provided model.
            - It will also have the standard AbstractCustomRelation fields:
              ``content_type``, ``object_id``, and the GenericForeignKey ``content_object``.
    """
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
