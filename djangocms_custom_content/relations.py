"""Grouper-anchored generic relations.

A sound replacement for the hand-rolled generic M2M in :mod:`models`. The two
ideas that make it correct and familiar:

1. **Relations are anchored to the grouper's stable primary key**, never to a
   versioned content row. djangocms-versioning copies content into new rows
   with new pks; anchoring to the grouper means relations survive version
   copies untouched.
2. **It leans on the Django ORM.** Storage is an ordinary through model with a
   concrete ``source`` :class:`~django.db.models.ForeignKey` and a
   :class:`~django.contrib.contenttypes.fields.GenericForeignKey` ``target``.
   The accessors return real :class:`~django.db.models.QuerySet` objects, so
   ``.filter()``, ``.order_by()``, ``.count()`` and friends just work.

Mental model: it is django-taggit, but the "tags" are grouper objects and each
relation gets its own through table.

Declarative usage on a grouper, reading like ``ManyToManyField``::

    class BlogPost(AbstractCustomGrouper):
        authors = RelationField("people.Person", related_name="authored_posts", ordered=True)

``related_name`` is the invitation: the reverse accessor appears on the target
grouper without that model importing or declaring anything. ``ordered`` is an
opt-in feature; without it no ordering column is created.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import TYPE_CHECKING, Any, cast

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.db.models.base import ModelBase
from django.db.models.signals import post_delete
from django.dispatch import receiver

# Through models created via :func:`relation_through_factory`. Tracked so the
# target-side cascade receiver knows which tables to sweep on delete.
_through_registry: set[type[models.Model]] = set()


# --------------------------------------------------------------------------- #
# Grouper resolution
# --------------------------------------------------------------------------- #
def _grouper_fk(content_model: type[models.Model]):
    """Return the FK field from a content model to its grouper, or ``None``.

    Resolved structurally (a content model carries a ForeignKey to an
    :class:`AbstractCustomGrouper`) so it works at import time, before the
    cms_config registry is populated.
    """
    from djangocms_custom_content.models import AbstractCustomGrouper, CustomContentMixin

    if not issubclass(content_model, CustomContentMixin):
        return None
    # local_fields only: forward fields defined on the model. Avoids
    # get_fields(), which builds the reverse-relation tree and would require
    # the full app registry (not available during lazy target binding).
    for field in content_model._meta.local_fields:
        if isinstance(field, models.ForeignKey) and issubclass(field.related_model, AbstractCustomGrouper):
            return field
    return None


def grouper_model_of(model: type[models.Model]) -> type[models.Model]:
    """Return the grouper model for a content model, else ``model`` unchanged.

    Relations always target the *grouper* so they survive version copies. A
    declaration may name either the grouper or its content model; both resolve
    here to the grouper ("if there is one").
    """
    from djangocms_custom_content.models import AbstractCustomGrouper

    if issubclass(model, AbstractCustomGrouper):
        return model
    fk = _grouper_fk(model)
    return fk.related_model if fk else model


def grouper_of(obj: models.Model) -> models.Model:
    """Return the grouper instance for a content instance, else ``obj``.

    Lets callers pass either a content object or a grouper to ``add()`` /
    ``remove()`` and always store the stable grouper pk.
    """
    fk = _grouper_fk(type(obj))
    return getattr(obj, fk.name) if fk else obj


# --------------------------------------------------------------------------- #
# Through models
# --------------------------------------------------------------------------- #
class CustomRelation(models.Model):
    """Abstract through model: a concrete ``source`` plus a generic ``target``.

    The ``source`` foreign key is added per-table by
    :func:`relation_through_factory`; it points at the owning grouper. The
    target is a :class:`GenericForeignKey` so a single table can relate the
    owner to groupers of any type.
    """

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name="+")
    object_id = models.PositiveIntegerField()
    target = GenericForeignKey("content_type", "object_id")

    if TYPE_CHECKING:
        # Concrete ``source`` FK is added per-table by relation_through_factory.
        source: models.ForeignKey

    class Meta:
        abstract = True

    def __str__(self) -> str:
        return f"{self.source} → {self.target}"


class OrderedCustomRelation(CustomRelation):
    """Through model variant carrying an explicit ``order`` column (opt-in)."""

    order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        abstract = True
        ordering = ["order"]


def relation_through_factory(
    owner_model: type[models.Model],
    *,
    ordered: bool = False,
    name: str | None = None,
    module: str | None = None,
) -> type[models.Model]:
    """Build a concrete through model linking ``owner_model`` to any grouper.

    The returned model has a concrete ``source`` FK to ``owner_model``, the
    inherited generic ``target``, a uniqueness constraint preventing duplicate
    edges and an index on the generic columns for fast reverse lookups.
    """
    base = OrderedCustomRelation if ordered else CustomRelation
    meta_attrs: dict = {
        "app_label": owner_model._meta.app_label,
        "constraints": [
            models.UniqueConstraint(
                fields=["source", "content_type", "object_id"],
                name="%(app_label)s_%(class)s_uniq",
            )
        ],
        "indexes": [models.Index(fields=["content_type", "object_id"])],
    }
    if ordered:
        meta_attrs["ordering"] = ["order"]
    attrs = {
        "source": models.ForeignKey(owner_model, on_delete=models.CASCADE, related_name="+"),
        "Meta": type("Meta", (), meta_attrs),
        "__module__": module or owner_model.__module__,
    }
    through = cast("type[models.Model]", ModelBase(name or f"{owner_model.__name__}Relation", (base,), attrs))
    _through_registry.add(through)
    return through


# --------------------------------------------------------------------------- #
# Managers (always return real querysets)
# --------------------------------------------------------------------------- #
def _content_type_for(model: type[models.Model]) -> ContentType:
    return ContentType.objects.get_for_model(model, for_concrete_model=False)


def _unique_groupers(objs: Iterable[models.Model]) -> list[models.Model]:
    """Return grouper-normalized objects, preserving first-seen order."""
    groupers = []
    seen = set()
    for obj in objs:
        grouper = grouper_of(obj)
        if grouper.pk is None:
            raise ValueError("Relations can only be created for saved model instances.")
        if grouper.pk in seen:
            continue
        seen.add(grouper.pk)
        groupers.append(grouper)
    return groupers


class RelationManager:
    """Forward accessor ``owner.<field>`` → a queryset of target groupers.

    ``through`` rows are filtered by ``source=owner``; the target groupers are
    returned as a genuine queryset so all queryset methods are available. When
    the through is ordered, results are ordered by the through's ``order``.
    """

    def __init__(
        self,
        instance: models.Model,
        through: type[models.Model],
        target_model: type[models.Model],
        *,
        ordered: bool,
    ):
        self.instance = instance
        self.through = through
        self.target_model = target_model
        self.ordered = ordered

    def _edges(self) -> models.QuerySet:
        return self.through.objects.filter(source=self.instance)

    def get_queryset(self) -> models.QuerySet:
        edges = self._edges()
        qs = self.target_model._default_manager.filter(pk__in=edges.values("object_id"))
        if self.ordered:
            order = edges.filter(object_id=models.OuterRef("pk")).values("order")[:1]
            qs = qs.annotate(_relation_order=models.Subquery(order)).order_by("_relation_order")
        return qs

    # Read API delegates to a real queryset.
    def all(self) -> models.QuerySet:
        return self.get_queryset()

    def filter(self, *args: Any, **kwargs: Any) -> models.QuerySet:
        return self.get_queryset().filter(*args, **kwargs)

    def count(self) -> int:
        return self._edges().count()

    def exists(self) -> bool:
        return self._edges().exists()

    def __iter__(self) -> Iterator[models.Model]:
        return iter(self.get_queryset())

    # Write API normalises content → grouper and stores the stable pk.
    def add(self, *objs: models.Model) -> None:
        groupers = _unique_groupers(objs)
        if not groupers:
            return
        ct = _content_type_for(self.target_model)
        next_order = (self._edges().aggregate(models.Max("order"))["order__max"] or 0) if self.ordered else 0
        rows = []
        for grouper in groupers:
            row = self.through(source=self.instance, content_type=ct, object_id=grouper.pk)
            if self.ordered:
                next_order += 1
                row.order = next_order
            rows.append(row)
        self.through.objects.bulk_create(rows, ignore_conflicts=True)

    def remove(self, *objs: models.Model) -> None:
        ct = _content_type_for(self.target_model)
        ids = [grouper_of(obj).pk for obj in objs]
        self._edges().filter(content_type=ct, object_id__in=ids).delete()

    def set(self, objs: Iterable[models.Model]) -> None:
        groupers = _unique_groupers(objs)
        ct = _content_type_for(self.target_model)
        new_ids = [grouper.pk for grouper in groupers]
        with transaction.atomic():
            existing_edges = {edge.object_id: edge for edge in self._edges().filter(content_type=ct)}
            removed_edge_pks = [edge.pk for object_id, edge in existing_edges.items() if object_id not in new_ids]
            if removed_edge_pks:
                self.through.objects.filter(pk__in=removed_edge_pks).delete()
            existing = {object_id: edge for object_id, edge in existing_edges.items() if object_id in new_ids}
            missing = []
            for position, grouper in enumerate(groupers):
                if grouper.pk in existing:
                    continue
                row = self.through(source=self.instance, content_type=ct, object_id=grouper.pk)
                if self.ordered:
                    row.order = position
                missing.append(row)
            self.through.objects.bulk_create(missing, ignore_conflicts=True)
            if self.ordered:
                updates = []
                for position, object_id in enumerate(new_ids):
                    edge = existing.get(object_id)
                    if edge is not None and edge.order != position:
                        edge.order = position
                        updates.append(edge)
                if updates:
                    self.through.objects.bulk_update(updates, ["order"])

    def clear(self) -> None:
        self._edges().delete()

    def reorder(self, objs: Iterable[models.Model]) -> None:
        """Set explicit ordering from an iterable of grouper/content objects."""
        if not self.ordered:
            raise TypeError("reorder() requires ordered=True on the relation")
        ct = _content_type_for(self.target_model)
        order = {grouper.pk: position for position, grouper in enumerate(_unique_groupers(objs))}
        if not order:
            return
        updates = []
        for edge in self._edges().filter(content_type=ct, object_id__in=order):
            new_order = order[edge.object_id]
            if edge.order != new_order:
                edge.order = new_order
                updates.append(edge)
        if updates:
            self.through.objects.bulk_update(updates, ["order"])


class ReverseRelationManager:
    """Reverse accessor ``target.<related_name>`` → queryset of source groupers."""

    def __init__(self, instance: models.Model, through: type[models.Model], source_model: type[models.Model]):
        self.instance = instance
        self.through = through
        self.source_model = source_model

    def _edges(self) -> models.QuerySet:
        ct = _content_type_for(type(self.instance))
        return self.through.objects.filter(content_type=ct, object_id=self.instance.pk)

    def get_queryset(self) -> models.QuerySet:
        return self.source_model._default_manager.filter(pk__in=self._edges().values("source_id"))

    def all(self) -> models.QuerySet:
        return self.get_queryset()

    def filter(self, *args: Any, **kwargs: Any) -> models.QuerySet:
        return self.get_queryset().filter(*args, **kwargs)

    def count(self) -> int:
        return self._edges().count()

    def exists(self) -> bool:
        return self._edges().exists()

    def __iter__(self) -> Iterator[models.Model]:
        return iter(self.get_queryset())

    def add(self, *objs: models.Model) -> None:
        groupers = _unique_groupers(objs)
        if not groupers:
            return
        ct = _content_type_for(type(self.instance))
        self.through.objects.bulk_create(
            [self.through(source=grouper, content_type=ct, object_id=self.instance.pk) for grouper in groupers],
            ignore_conflicts=True,
        )

    def remove(self, *objs: models.Model) -> None:
        sources = [grouper_of(obj).pk for obj in objs]
        self._edges().filter(source_id__in=sources).delete()

    def clear(self) -> None:
        self._edges().delete()


# --------------------------------------------------------------------------- #
# Descriptors
# --------------------------------------------------------------------------- #
class RelationDescriptor:
    def __init__(self, field):
        self.field = field

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return RelationManager(instance, self.field.through, self.field.target_model, ordered=self.field.ordered)


def iter_relation_fields(model: type[models.Model]):
    """Yield ``(name, RelationField)`` for each forward relation on ``model``."""
    seen = set()
    for klass in model.__mro__:
        for name, attr in vars(klass).items():
            if isinstance(attr, RelationDescriptor) and name not in seen:
                seen.add(name)
                yield name, attr.field


class ReverseRelationDescriptor:
    def __init__(self, through: type[models.Model], source_model: type[models.Model]):
        self.through = through
        self.source_model = source_model

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return ReverseRelationManager(instance, self.through, self.source_model)


# --------------------------------------------------------------------------- #
# Declarative field
# --------------------------------------------------------------------------- #
class RelationField:
    """Declarative grouper-to-grouper relation, à la ``ManyToManyField``.

    ``target`` may be a model class or an ``"app_label.Model"`` string naming
    either a grouper or its content model (resolved to the grouper). The
    forward accessor is installed immediately; the reverse accessor named by
    ``related_name`` is installed on the target once the app registry is ready.
    """

    def __init__(self, target, *, related_name=None, ordered=False, through_name=None):
        self._target_ref = target
        self.related_name = related_name
        self.ordered = ordered
        self.through_name = through_name
        self.name = None
        self.owner_model = None
        self.target_model = None
        self.through = None

    def contribute_to_class(self, cls, name):
        self.name = name
        self.owner_model = cls
        through_name = self.through_name or f"{cls.__name__}{name.title().replace('_', '')}Relation"
        self.through = relation_through_factory(cls, ordered=self.ordered, name=through_name)
        setattr(cls, name, RelationDescriptor(self))

        # The target (and thus its grouper) may not be importable yet; resolve
        # lazily and only then bind the queryset target + reverse accessor.
        if isinstance(self._target_ref, str):
            app_label, model_name = self._target_ref.split(".")
            cls._meta.apps.lazy_model_operation(self._bind_target, (app_label, model_name.lower()))
        else:
            self._bind_target(self._target_ref)

    def _bind_target(self, target_model):
        self.target_model = grouper_model_of(target_model)
        if self.related_name:
            # contribute_to_class (which sets through/owner_model) always runs first.
            assert self.through is not None and self.owner_model is not None
            setattr(
                self.target_model,
                self.related_name,
                ReverseRelationDescriptor(self.through, self.owner_model),
            )


# --------------------------------------------------------------------------- #
# Target-side cascade
# --------------------------------------------------------------------------- #
@receiver(post_delete)
def _cleanup_relations_on_target_delete(sender, instance, **kwargs):
    """Delete dangling relation rows when a target grouper is deleted.

    The concrete ``source`` FK cascades natively; the generic ``target`` has no
    database constraint, so its rows are swept here. Cheap: skipped entirely
    unless relation tables exist, and only ever runs for grouper instances
    (the only thing a relation can target).
    """
    from djangocms_custom_content.models import AbstractCustomGrouper

    if not _through_registry or not isinstance(instance, AbstractCustomGrouper):
        return
    ct = _content_type_for(sender)
    for through in _through_registry:
        through.objects.filter(content_type=ct, object_id=instance.pk).delete()
