Set Up Many-to-Many Relations
=============================

Relating content to content takes one line. Add a
:class:`~djangocms_custom_content.relations.RelationField` to a **grouper** model
— it reads just like Django's ``ManyToManyField``:

.. code-block:: python

    from djangocms_custom_content.relations import RelationField

    class BlogPost(AbstractCustomGrouper):
        authors = RelationField("people.Person", related_name="authored_posts", ordered=True)

Run ``makemigrations`` and you're done — ``post.authors.add(person)`` and
``person.authored_posts.all()`` both work, and the admin renders ``authors`` as a
sortable autocomplete. The rest of this guide unpacks the options.

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

.. note::

   Ordering belongs to the **edge list**, so it applies to the forward accessor
   only. ``ordered=True`` on ``BlogPost.authors`` orders the authors *within a
   post*; it says nothing about the order of ``person.authored_posts``, which
   comes back in the target model's default order.

In templates
~~~~~~~~~~~~

Because accessors return groupers, reach the displayable content through the
grouper — with ``get_content`` on the front end and ``get_admin_content`` in the
admin:

.. code-block:: django

    {% for person in post.authors.all %}
        {% with profile=person.get_content %}
            {% if profile %}<strong>{{ profile.name }}</strong>{% endif %}
        {% endwith %}
    {% endfor %}

    {% for category in post.categories.all %}
        <span class="category">{{ category.title }}</span>
    {% endfor %}

.. warning::

   Use ``get_content`` for anything a visitor sees. ``get_admin_content``
   returns the **latest** content including unpublished drafts, so on a public
   page it leaks work in progress.

.. note::

   ``FlatCategory`` is a grouper-less content model, so its accessor yields the
   ``FlatCategory`` objects directly (``category.title`` above), while
   ``Person`` is a grouper, so its content is reached via ``get_content``.

.. _rendering-relations-in-a-detail-view:

Rendering relations in a detail view
------------------------------------

A detail view is handed a **content** object, but relations live on **groupers**.
Rendering "every blog post this person authored" is therefore a two-hop walk:

.. code-block:: text

    PersonContent  ->  Person  ->  BlogPost (groupers)  ->  BlogPostContent
     the content       .person    .authored_posts.all()     .get_content()
     being rendered    grouper     the reverse accessor      what you display

The catch is the last hop. The accessor returns groupers regardless of
publication state, and ``get_content()`` returns ``None`` for any grouper whose
content is not published — so a naive loop renders blank entries for drafts and
unpublished posts.

Doing it in the view
~~~~~~~~~~~~~~~~~~~~

Resolve the content once, drop the ``None``\ s, and hand the template a plain
list. This is the shape to prefer: the filtering is explicit, and the template
stays free of logic.

.. code-block:: python

    from djangocms_custom_content.views import custom_detail_view_factory
    from djangocms_custom_content.contrib.people.models import PersonContent


    class PersonDetailView(custom_detail_view_factory(PersonContent)):
        def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            posts = self.object.person.authored_posts.all()
            # get_content() is None for posts that are not published.
            context["posts"] = [content for post in posts if (content := post.get_content())]
            return context

.. code-block:: django

    <h2>Posts by {{ personcontent.name }}</h2>
    <ul>
      {% for post in posts %}
        <li>{{ post.title }}</li>
      {% empty %}
        <li>No published posts yet.</li>
      {% endfor %}
    </ul>

To use the view, register it yourself rather than relying on the generated
apphook (see :doc:`apphooks`).

Doing it in the template
~~~~~~~~~~~~~~~~~~~~~~~~

If you would rather not write a view, the same walk works in the template — the
``{% if %}`` is what skips unpublished posts:

.. code-block:: django

    <h2>Posts by {{ personcontent.name }}</h2>
    <ul>
      {% for post in personcontent.person.authored_posts.all %}
        {% with content=post.get_content %}
          {% if content %}<li>{{ content.title }}</li>{% endif %}
        {% endwith %}
      {% endfor %}
    </ul>

This costs one query per post, so prefer the view for anything but a short list.

Counting is cheaper than listing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``count()`` and ``exists()`` run against the through table alone and never touch
the target model, so they are cheap — but for the same reason they count
**edges**, not published posts:

.. code-block:: python

    person.authored_posts.count()    # includes unpublished posts

If the number has to match the list you rendered, count the resolved list
instead.

Deleting targets
----------------

The concrete source foreign key cascades natively. The generic target has no
database constraint, so when a target grouper is deleted the framework sweeps
its dangling relation rows automatically.

Copying
-------

Edges are anchored to the grouper, so **creating a new version copies nothing** —
the new version sees the same relations. They are only not carried over when you
**duplicate the grouper itself** (just like a Django ``ManyToManyField``); copy
them explicitly in that case:

.. code-block:: python

    from djangocms_custom_content.relations import iter_relation_fields

    for name, _field in iter_relation_fields(type(source_grouper)):
        getattr(new_grouper, name).set(getattr(source_grouper, name).all())

A full duplicate usually also re-creates the grouper's **content** object(s)
(pointed at ``new_grouper``) — a brand-new grouper has no content of its own.

See :doc:`../explanation/relationships` for the full rationale.

See Also
--------

- :doc:`../reference/index` - API reference
- :doc:`../explanation/relationships` - How the relation storage works
- :doc:`../tutorials/model_with_m2m` - Step-by-step tutorial
