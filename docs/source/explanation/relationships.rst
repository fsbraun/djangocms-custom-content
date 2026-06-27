Relations Explained
===================

djangocms-custom-content models many-to-many relations between content with a
single declarative field,
:class:`~djangocms_custom_content.relations.RelationField`, declared on a
**grouper** model. This page explains how it works under the hood and why it is
designed that way.

Two ideas make it correct and familiar
--------------------------------------

1. **Relations are anchored to the grouper's stable primary key**, never to a
   versioned content row. djangocms-versioning copies content into new rows with
   new primary keys; anchoring to the grouper means relations survive version
   copies untouched.
2. **It leans on the Django ORM.** Storage is an ordinary through model with a
   concrete ``source`` :class:`~django.db.models.ForeignKey` and a
   :class:`~django.contrib.contenttypes.fields.GenericForeignKey` ``target``.
   The accessors return real querysets, so ``.filter()``, ``.order_by()``,
   ``.count()`` and friends just work.

The Through Model
-----------------

A standard Django ``ManyToManyField`` generates an automatic through model with
two concrete foreign keys — one to each side. That only works for relating to
**one** specific model type.

Instead, :func:`~djangocms_custom_content.relations.relation_through_factory`
builds a concrete through model per relation that uses:

- **one concrete ForeignKey** (``source``) to the owning grouper, and
- **one GenericForeignKey** (``target``, via ``content_type`` + ``object_id``)
  that can point at a grouper of *any* type.

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Column
     - Purpose
   * - ``source``
     - FK to the owning grouper (e.g. ``BlogPost``)
   * - ``content_type``
     - Which grouper *type* the edge points at
   * - ``object_id``
     - Primary key of the target grouper
   * - ``target``
     - GenericForeignKey resolving ``content_type`` + ``object_id``
   * - ``order``
     - Position column, **only** when ``ordered=True``

Each through table carries a uniqueness constraint over
``(source, content_type, object_id)`` so an edge cannot be duplicated, plus an
index on ``(content_type, object_id)`` for fast reverse lookups. Ordered
relations use the :class:`~djangocms_custom_content.relations.OrderedCustomRelation`
base, which adds the indexed ``order`` column.

Grouper resolution
------------------

A ``RelationField`` target may name either a grouper or its content model. Both
resolve to the grouper via
:func:`~djangocms_custom_content.relations.grouper_model_of`, which finds the
foreign key from a content model to its
:class:`~djangocms_custom_content.models.AbstractCustomGrouper`. Likewise,
``add()`` / ``remove()`` accept either a grouper or a content instance and store
the stable grouper primary key (``grouper_of``). A model with no grouper (such as
the standalone ``FlatCategory``) simply resolves to itself.

Forward and reverse accessors
-----------------------------

Declaring the field installs a
:class:`~djangocms_custom_content.relations.RelationManager` as the forward
accessor on the owner. If ``related_name`` is given, a
:class:`~djangocms_custom_content.relations.ReverseRelationManager` is installed
on the target grouper once the app registry is ready — the target model imports
or declares nothing.

.. code-block:: python

    class BlogPost(AbstractCustomGrouper):
        authors = RelationField(
            "people.Person", related_name="authored_posts", ordered=True,
        )

    post.authors.all()           # forward: Person groupers for this post
    person.authored_posts.all()  # reverse: BlogPost groupers for this person

Both managers expose the same read API (``all``, ``filter``, ``count``,
``exists``, iteration) and write API (``add``, ``remove``, ``clear``; the
forward manager additionally has ``set`` and, for ordered relations,
``reorder``). Reads always go through a genuine queryset of the related groupers.

Target-side cascade
-------------------

The concrete ``source`` foreign key cascades natively on delete. The generic
``target`` has no database-level constraint, so a ``post_delete`` receiver sweeps
dangling rows when a target grouper is deleted. It is cheap: skipped entirely
unless relation tables exist, and it only runs for grouper instances.

Copying: versioning vs. duplicating a grouper
---------------------------------------------

Because edges live on the grouper, there are two distinct cases — and only one of
them needs your attention:

- **Creating a new version** (djangocms-versioning copies the *content* row): the
  grouper keeps its primary key, so the edges are untouched and the new version
  sees the same relations. Nothing to do — this is the point of anchoring to the
  grouper.
- **Duplicating the grouper itself** (a hand-rolled "duplicate this object"
  action that creates a *new* grouper): edges are **not** copied automatically,
  exactly as a Django ``ManyToManyField`` is not copied when you save an instance
  with ``pk=None``. Copy them explicitly:

  .. code-block:: python

      from djangocms_custom_content.relations import iter_relation_fields

      for name, _field in iter_relation_fields(type(source_grouper)):
          getattr(new_grouper, name).set(getattr(source_grouper, name).all())

  ``.set()`` re-adds in queryset order, so ``ordered=True`` relations keep their
  positions.

  Copying edges is only half of it: a fresh grouper has **no content**, since the
  editable data lives in the content rows, not the grouper. A complete "duplicate
  this object" also re-creates the relevant content object(s) — typically one per
  language, or a new draft version — pointing their grouper foreign key at
  ``new_grouper`` before (or after) you copy the relations. How many content rows
  to copy is app-specific, so the framework leaves it to you.

See Also
--------

- :doc:`../how-to/m2m_relations` - Practical implementation guide
- :doc:`../tutorials/model_with_m2m` - Step-by-step tutorial
- :doc:`../reference/index` - API reference
