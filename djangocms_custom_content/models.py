from cms.models.fields import PlaceholderRelationField
from cms.models.managers import ContentAdminManager, WithUserMixin
from django.core.exceptions import ValidationError
from django.db import models
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
        _content_accessor_name: Name of the reverse accessor to the content model
        _has_language_field: Whether the content model has a language field
        _content_cache: Cache for retrieved content instances
        _is_admin_cache: Flag for admin-specific caching
    """

    class Meta:
        abstract = True

    # Describe the *model*, so they are resolved once and cached on the class.
    _content_accessor_name: str | None = None
    _content_relation_resolved = False
    _custom_model: type[models.Model] | None = None
    _grouper_field_name: str | None = None
    _has_language_field = False
    _content_cache: models.Model | dict[str, models.Model] | None = None
    _admin_prefetch_cache: list[models.Model]
    _is_admin_cache = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.__class__._content_relation_resolved:
            self.__class__._resolve_content_relation()

    @classmethod
    def _resolve_content_relation(cls) -> None:
        """Identify the reverse relation to this grouper's custom content model.

        Only names are cached on the class -- never the related manager itself, which is
        bound to the instance it was read from. Sharing one would make every grouper of a
        model report the first instantiated grouper's content.
        """
        for field in cls._meta.get_fields():
            if isinstance(field, ForeignObjectRel) and issubclass(field.related_model, CustomContentMixin):
                accessor = field.get_accessor_name()
                if accessor:
                    cls._content_accessor_name = accessor
                    cls._custom_model = field.related_model
                    config = get_custom_config(field.related_model)
                    cls._grouper_field_name = config[1]
                    cls._has_language_field = config[2]
                    # ``cms_config`` may not be populated yet when the first instance is
                    # created (during app loading, say), so retry until it answers.
                    cls._content_relation_resolved = bool(config[1])
                    return
        # No content model relates to this grouper: there is nothing to look up again.
        cls._content_relation_resolved = True

    @property
    def _content_set(self):
        """The related manager for *this* instance's content objects, or ``None`` when no
        content model relates to this grouper."""
        if self._content_accessor_name is None:
            return None
        return getattr(self, self._content_accessor_name)

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
        return self._get_content(language or get_language(), self._content_set.all())

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
            if self._has_language_field:
                self._content_cache = {obj.language: obj for obj in self._admin_prefetch_cache}
            else:
                self._content_cache = self._admin_prefetch_cache[0] if self._admin_prefetch_cache else None
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

    To relate content groupers to one another, declare a
    :class:`~djangocms_custom_content.relations.RelationField` on the grouper
    model. See :mod:`djangocms_custom_content.relations`.
    """

    objects = CustomContentManager()
    admin_manager = ContentAdminManager()

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

    @classmethod
    def has_slug_field(cls) -> bool:
        return any(field.name == "slug" for field in cls._meta.get_fields())

    @classmethod
    def find_slug_conflicts(cls, slug: str | None, language: str | None = None, grouper_id=None) -> models.QuerySet:
        """Content of *other* objects that already uses ``slug``.

        A detail URL has to identify a single object, so a slug may be repeated
        only within one grouper -- across its versions and, where the content has
        a ``language`` field, across its translations.

        Deliberately checks **every** version rather than only the current one: a
        slug held by an archived version of another object comes back the moment
        that version is reverted, and an ambiguous URL is worse than a rejected
        one.
        """
        grouper_field_name = get_custom_config(cls)[1]
        if not grouper_field_name or not cls.has_slug_field() or not slug:
            return cls.admin_manager.none()

        conflicts = cls.admin_manager.filter(slug=slug)
        if language is not None and any(field.name == "language" for field in cls._meta.get_fields()):
            conflicts = conflicts.filter(language=language)
        if grouper_id is not None:
            conflicts = conflicts.exclude(**{f"{grouper_field_name}_id": grouper_id})
        return conflicts

    @classmethod
    def slug_conflict_message(cls) -> str:
        return _("Another %(name)s already uses this slug.") % {"name": cls._meta.verbose_name}

    def validate_unique(self, exclude=None) -> None:
        """Reject a slug that another object already uses."""
        super().validate_unique(exclude)
        if exclude and "slug" in exclude:
            return
        grouper_field_name = get_custom_config(type(self))[1]
        if not grouper_field_name:
            return
        conflicts = type(self).find_slug_conflicts(
            getattr(self, "slug", None),
            language=getattr(self, "language", None),
            grouper_id=getattr(self, f"{grouper_field_name}_id", None),
        )
        if conflicts.exists():
            raise ValidationError({"slug": self.slug_conflict_message()})
