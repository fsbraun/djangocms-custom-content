from cms.models.fields import PlaceholderRelationField
from cms.models.managers import ContentAdminManager, WithUserMixin
from django.apps import apps
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.base import ModelBase
from django.db.models.fields.reverse_related import ForeignObjectRel
from django.db.models.signals import class_prepared
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

    Many-to-many relationships to other models are declared via ``CMSConfig.m2m``::

        class BlogPostContent(AbstractCustomContent):
            class CMSConfig:
                m2m = [
                    ("authors", "people.Person"),                 # auto-reverse: blogpost_set
                    ("tags", "tags.Tag", "blog_posts"),           # explicit reverse name
                    ("featured", "promo.Promo", None),            # no reverse accessor
                ]

    For each declaration the framework creates a single through-model named
    ``{ContentModelName}Relation`` in the declaring model's app, with an FK to
    the model's grouper (or to the content model itself if there is no grouper).
    The forward accessor is installed on that grouper/content model, and a
    reverse accessor is installed on the target unless explicitly disabled.
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


class AbstractCustomRelation(models.Model):
    """
    Abstract base for the through-model used by custom m2m relations.

    Users do not subclass this directly; the framework generates a concrete
    subclass automatically from each ``CMSConfig.m2m`` declaration. The
    generated class has:

    * an ``instance`` ForeignKey pointing to the declarer (its grouper, or the
      content model itself if it has no grouper);
    * ``content_type`` + ``object_id`` (and the ``content_object`` GFK)
      pointing to the relation's target.
    """

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_("content type"),
    )
    object_id = models.PositiveIntegerField(
        _("object id"),
    )
    content_object = GenericForeignKey("content_type", "object_id")
    relation_name = models.CharField(_("relation name"), max_length=100)
    order = models.PositiveIntegerField(_("order"), default=0)

    instance = None  # Concrete subclasses replace this with a ForeignKey

    class Meta:
        abstract = True
        ordering = ("order", "pk")

    def __str__(self) -> str:
        return f"{self.instance} -[{self.relation_name}]-> {self.content_object}"


FK_SIDE = "fk"
GFK_SIDE = "gfk"


class _CustomM2MManager:
    """Manager returned by :class:`_CustomM2MDescriptor`.

    Handles both directions of a custom m2m relation:

    * ``side=FK_SIDE`` — the instance is the declarer (FK column of the
      through-model). Used by the forward accessor on the owner.
    * ``side=GFK_SIDE`` — the instance is the target (GFK column). Used by the
      reverse accessor.

    ``relation_name`` disambiguates multiple relations that share the same
    through-table and target model (e.g. ``authors`` and ``editors`` both
    pointing to Person).
    """

    def __init__(self, instance, through_model, target_model, *, side, relation_name):
        self.instance = instance
        self.through_model = through_model
        self.target_model = target_model
        self.side = side
        self.relation_name = relation_name

    def _through_qs(self):
        filters = {"relation_name": self.relation_name}
        if self.side == FK_SIDE:
            filters["instance"] = self.instance
            filters["content_type"] = ContentType.objects.get_for_model(self.target_model)
        else:
            filters["content_type"] = ContentType.objects.get_for_model(type(self.instance))
            filters["object_id"] = self.instance.pk
        return self.through_model.objects.filter(**filters)

    def _target_pk_field(self):
        return "object_id" if self.side == FK_SIDE else "instance_id"

    def _target_manager(self):
        return getattr(self.target_model, "admin_manager", None) or self.target_model._default_manager

    def all(self):
        """Return a queryset of related target objects, ordered by the through-table's ``order``."""
        from django.db.models import OuterRef, Subquery

        target_pk_field = self._target_pk_field()
        through_qs = self._through_qs()
        order_lookup = through_qs.filter(**{target_pk_field: OuterRef("pk")}).values("order")[:1]
        return (
            self._target_manager()
            .filter(pk__in=through_qs.values_list(target_pk_field, flat=True))
            .annotate(_m2m_order=Subquery(order_lookup))
            .order_by("_m2m_order")
        )

    def filter(self, *args, **kwargs):
        return self.all().filter(*args, **kwargs)

    def count(self):
        return self._through_qs().count()

    def exists(self):
        return self._through_qs().exists()

    def _next_order(self):
        last = self._through_qs().order_by("-order").values_list("order", flat=True).first()
        return (last or 0) + 1

    def add(self, *objs):
        order = self._next_order()
        for obj in objs:
            if self.side == FK_SIDE:
                _row, created = self.through_model.objects.get_or_create(
                    instance=self.instance,
                    content_type=ContentType.objects.get_for_model(self.target_model),
                    object_id=obj.pk,
                    relation_name=self.relation_name,
                    defaults={"order": order},
                )
            else:
                _row, created = self.through_model.objects.get_or_create(
                    instance=obj,
                    content_type=ContentType.objects.get_for_model(type(self.instance)),
                    object_id=self.instance.pk,
                    relation_name=self.relation_name,
                    defaults={"order": order},
                )
            if created:
                order += 1

    def set(self, objs):
        """Replace the current set of relations with ``objs`` in the given order.

        Existing rows for relations not in ``objs`` are deleted; existing rows
        for relations that remain have their ``order`` updated to match the
        position in ``objs``.
        """
        objs = list(objs)
        keep_pks = [o.pk for o in objs]
        # Delete rows for relations no longer present
        if self.side == FK_SIDE:
            self._through_qs().exclude(object_id__in=keep_pks).delete()
        else:
            self._through_qs().exclude(instance_id__in=keep_pks).delete()

        # Upsert remaining rows with the new ordering
        for pos, obj in enumerate(objs):
            if self.side == FK_SIDE:
                self.through_model.objects.update_or_create(
                    instance=self.instance,
                    content_type=ContentType.objects.get_for_model(self.target_model),
                    object_id=obj.pk,
                    relation_name=self.relation_name,
                    defaults={"order": pos},
                )
            else:
                self.through_model.objects.update_or_create(
                    instance=obj,
                    content_type=ContentType.objects.get_for_model(type(self.instance)),
                    object_id=self.instance.pk,
                    relation_name=self.relation_name,
                    defaults={"order": pos},
                )

    def remove(self, *objs):
        pks = [o.pk for o in objs]
        if self.side == FK_SIDE:
            self._through_qs().filter(object_id__in=pks).delete()
        else:
            self._through_qs().filter(instance_id__in=pks).delete()

    def clear(self):
        self._through_qs().delete()


class _CustomM2MDescriptor:
    """Descriptor that returns a :class:`_CustomM2MManager` bound to an instance."""

    def __init__(self, through_model, target_model, side, relation_name):
        self.through_model = through_model
        self.target_model = target_model
        self.side = side
        self.relation_name = relation_name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return _CustomM2MManager(
            instance,
            self.through_model,
            self.target_model,
            side=self.side,
            relation_name=self.relation_name,
        )


class _DummyM2MManager:
    """No-op manager returned when a relation's target model is not installed."""

    def all(self):
        return []

    def filter(self, *args, **kwargs):
        return []

    def count(self):
        return 0

    def exists(self):
        return False

    def add(self, *objs):
        pass

    def remove(self, *objs):
        pass

    def clear(self):
        pass


class _DummyM2MDescriptor:
    def __get__(self, instance, owner):
        if instance is None:
            return self
        return _DummyM2MManager()


_AUTO_REVERSE = object()


def _normalize_m2m_decl(decl):
    """Return ``(forward_name, target_label, reverse_name_or_sentinel)``.

    ``reverse_name_or_sentinel`` is ``_AUTO_REVERSE`` for 2-tuples (auto-derive
    the reverse name), ``None`` to explicitly disable the reverse accessor, or
    a string for an explicit reverse name.
    """
    if len(decl) == 2:
        return decl[0], decl[1], _AUTO_REVERSE
    if len(decl) == 3:
        return decl[0], decl[1], decl[2]
    raise ValueError(f"CMSConfig.m2m entries must be 2- or 3-tuples, got {decl!r}")


def _get_owner_for_content(content_cls):
    """Return the model that owns the relation (its grouper, or the content itself).

    Uses ``local_fields`` and ``remote_field.model`` directly so this can be
    called safely from a ``class_prepared`` handler (before the app registry
    is ready, ``field.related_model`` would raise ``AppRegistryNotReady``).
    """
    for field in content_cls._meta.local_fields:
        if not isinstance(field, models.ForeignKey):
            continue
        target = field.remote_field.model
        # Only handle direct class references — string refs ("app.Model") would
        # require resolving the app registry, and groupers are always available
        # by the time their content model is created.
        if isinstance(target, type) and issubclass(target, CustomGrouperMixin):
            return target
    return content_cls


def _through_model_name(content_cls):
    return f"{content_cls.__name__}Relation"


def _get_or_create_through_model(content_cls):
    """Return the through-model for ``content_cls``, creating it if needed."""
    through_name = _through_model_name(content_cls)
    # Use the private all_models registry: class_prepared fires before
    # apps.ready, so the public get_model() raises AppRegistryNotReady here.
    existing = apps.all_models.get(content_cls._meta.app_label, {}).get(through_name.lower())
    if existing is not None:
        return existing

    owner_cls = _get_owner_for_content(content_cls)
    return ModelBase(
        through_name,
        (AbstractCustomRelation,),
        {
            "instance": models.ForeignKey(owner_cls, on_delete=models.CASCADE, related_name="+"),
            "__module__": content_cls.__module__,
        },
    )


def _on_class_prepared(sender, **kwargs):
    """Auto-create the through-model for content classes that declare ``CMSConfig.m2m``."""
    try:
        if not issubclass(sender, AbstractCustomContent):
            return
    except TypeError:
        return
    cms_config = getattr(sender, "CMSConfig", None)
    if cms_config is None:
        return
    if not getattr(cms_config, "m2m", None):
        return
    _get_or_create_through_model(sender)


class_prepared.connect(_on_class_prepared)
