Set Up Many-to-Many Relations
=============================

djangocms-custom-content provides a single, declarative way to relate content to
other content: the :class:`~djangocms_custom_content.relations.RelationField`.
You declare it on a **grouper** model and it reads like Django's
``ManyToManyField``.

Why a custom field?
-------------------

Relations are anchored to the **grouper's** stable primary key, never to a
versioned content row. djangocms-versioning copies content into new rows with
new primary keys; anchoring to the grouper means relations survive version
copies untouched. A single relation can also target groupers of any type,
because storage uses a ``GenericForeignKey`` for the target.

Mental model: it is django-taggit, but the "tags" are grouper objects and each
relation gets its own through table.

Declaring a relation
---------------------

Declare ``RelationField`` on the grouper that *owns* the relation:

.. code-block:: python

    from djangocms_custom_content.models import AbstractCustomGrouper
    from djangocms_custom_content.relations import RelationField

    class BlogPost(AbstractCustomGrouper):
        authors = RelationField(
            "people.Person",
            related_name="authored_posts",
            ordered=True,
        )
        categories = RelationField(
            "categories.FlatCategory",
            related_name="blog_posts",
        )

``RelationField`` arguments:

``target``
    A model class or an ``"app_label.Model"`` string. You may name either the
    grouper or its content model; both resolve to the grouper. The string form
    is resolved lazily, so the target app need not be importable at declaration
    time.

``related_name``
    Installs a reverse accessor of this name on the *target* grouper. The target
    model does not import or declare anything — the reverse accessor simply
    appears once the app registry is ready.

``ordered`` (default ``False``)
    Opt in to an explicit ordering column on the through table. Only then is a
    :meth:`~djangocms_custom_content.relations.RelationManager.reorder` method
    available and results returned in stored order.

``through_name`` (optional)
    Override the auto-generated through model class name.

Each ``RelationField`` creates its own concrete through table with a uniqueness
constraint (no duplicate edges) and an index for fast reverse lookups. No
migration boilerplate is required beyond running ``makemigrations`` for the app
that declares the field.

Using the accessors
-------------------

The forward accessor lives on the owner grouper; the reverse accessor (if
``related_name`` was given) lives on the target grouper. Both return real
querysets, so ``.filter()``, ``.order_by()``, ``.count()`` and friends just work.

.. code-block:: python

    post = BlogPost.objects.first()
    person = Person.objects.first()

    # Write API — accepts a grouper OR a content object (normalised to grouper)
    post.authors.add(person)
    post.authors.remove(person)
    post.authors.set([person])
    post.authors.clear()

    # Read API — backed by a queryset of target groupers
    post.authors.all()
    post.authors.filter(...)
    post.authors.count()
    post.authors.exists()

    # Reverse accessor invited by related_name
    person.authored_posts.all()   # BlogPost groupers authored by this person

Ordered relations
-----------------

When the field is declared with ``ordered=True``, ``add()`` appends to the end
and you can set an explicit order with ``reorder()``:

.. code-block:: python

    post.authors.reorder([alice, bob, carol])
    post.authors.all()   # alice, bob, carol

``reorder()`` raises ``TypeError`` on a relation that is not ordered.

In templates
~~~~~~~~~~~~

Because accessors return groupers, reach the displayable content through the
grouper's ``get_admin_content`` (or ``get_content``):

.. code-block:: django

    {% for person in post.authors.all %}
        {% with profile=person.get_admin_content %}
            <strong>{{ profile.name }}</strong>
        {% endwith %}
    {% endfor %}

    {% for category in post.categories.all %}
        <span class="category">{{ category.title }}</span>
    {% endfor %}

.. note::

   ``FlatCategory`` is a grouper-less content model, so its accessor yields the
   ``FlatCategory`` objects directly (``category.title`` above), while
   ``Person`` is a grouper, so its content is reached via ``get_admin_content``.

Deleting targets
----------------

The concrete source foreign key cascades natively. The generic target has no
database constraint, so when a target grouper is deleted the framework sweeps
its dangling relation rows automatically.

See Also
--------

- :doc:`../reference/index` - API reference
- :doc:`../explanation/relationships` - How the relation storage works
- :doc:`../tutorials/model_with_m2m` - Step-by-step tutorial
