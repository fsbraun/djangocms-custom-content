M2M Relationships Explained
===========================

djangocms-custom-content offers a single declarative API for many-to-many
relationships between custom content models: ``CMSConfig.m2m``. This page
explains what the framework generates from that declaration and why the
design looks the way it does.

The Through Model
-----------------

A regular Django ``ManyToManyField`` creates an **automatic through table**
that links two specific models. That's perfect when the relation is fixed at
design time, but custom content often needs more flexibility:

- the same accessor should be able to point at content models from optional
  contrib apps;
- you don't want to maintain a hand-written join model per relation pair;
- the table should be language-independent (attached to the grouper rather
  than every language version).

To handle this, the framework generates one through-model per declaring
content class. The schema combines a **forward FK** to the declarer with a
**GenericForeignKey** to the target:

.. code-block:: python

    class BlogPostContentRelation(AbstractCustomRelation):
        instance = models.ForeignKey(BlogPost, on_delete=models.CASCADE)  # FK to grouper
        content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
        object_id = models.PositiveIntegerField()
        content_object = GenericForeignKey("content_type", "object_id")
        relation_name = models.CharField(max_length=100)

You never write this class by hand — the framework generates it from a
``CMSConfig.m2m`` declaration on the corresponding ``AbstractCustomContent``
subclass:

.. code-block:: python

    class BlogPostContent(AbstractCustomContent):
        post = models.ForeignKey(BlogPost, on_delete=models.CASCADE)

        class CMSConfig:
            m2m = [
                ("authors", "people.Person"),
                ("categories", "categories.FlatCategory"),
            ]

What lives where
----------------

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Field
     - Purpose
   * - ``instance``
     - FK to the declarer's grouper (or to the content model itself if it has
       no grouper). The relation lives on the grouper so it's the same across
       all language versions.
   * - ``content_type`` / ``object_id``
     - GenericForeignKey to the target object. Allows the same through-table
       to relate to any number of distinct target model types.
   * - ``content_object``
     - Virtual accessor that resolves the GFK to the actual target instance.
   * - ``relation_name``
     - Distinguishes multiple ``m2m`` entries that share the same
       through-table — e.g. ``("authors", "people.Person")`` and
       ``("editors", "people.Person")`` both store rows here but stay
       independent because the rows carry different ``relation_name`` values.

Why a GenericForeignKey?
------------------------

A single ``BlogPostContentRelation`` table can carry relations to *any*
target model. Conceptually, rows look like this:

.. code-block:: sql

    -- BlogPost 1 has author Person 2
    INSERT INTO blogpost_content_relation (instance_id, content_type_id, object_id, relation_name)
    VALUES (1, 42, 2, 'authors');   -- content_type 42 = Person

    -- BlogPost 1 is in category FlatCategory 7
    INSERT INTO blogpost_content_relation (instance_id, content_type_id, object_id, relation_name)
    VALUES (1, 43, 7, 'categories');   -- content_type 43 = FlatCategory

Both relations live in the same physical table, scoped by ``relation_name``.

Comparison: Django M2M vs. Custom M2M
-------------------------------------

.. list-table::
   :widths: 30 35 35
   :header-rows: 1

   * - Aspect
     - Standard Django M2M
     - djangocms-custom-content M2M
   * - Declaration
     - ``ManyToManyField`` on each model
     - One ``m2m`` entry per relation
   * - Through model
     - Auto-generated per pair, one table per relation
     - Auto-generated per declarer, one table per content model
   * - Flexibility
     - Fixed pair (Model A ↔ Model B)
     - Any target via GenericForeignKey
   * - Reverse accessor
     - Always created (``..._set``)
     - Auto by default, overridable, or suppressible
   * - Optional targets
     - Hard failure if target missing
     - Dummy accessor when target app not installed
   * - Language semantics
     - Attached to the model the field is on
     - Attached to the grouper (language-independent)

Accessor placement
------------------

The forward accessor is installed on the declarer's **owner**: the grouper if
one exists, otherwise the content model itself. The reverse accessor is
installed on the target.

.. code-block:: python

    class BlogPostContent(AbstractCustomContent):
        class CMSConfig:
            m2m = [("authors", "people.Person")]

    # owner = BlogPost (Person's grouper-having declarer)
    blog_post.authors           # forward — on grouper
    person.blogpost_set         # reverse — auto-named "{owner}_set"

The 3-tuple form lets you override or disable the reverse name:

.. code-block:: python

    m2m = [
        ("authors", "people.Person", "wrote"),   # person.wrote
        ("hidden", "people.Person", None),       # no reverse
    ]

Optional targets
----------------

If the target model isn't installed (e.g. an optional contrib app), the
forward accessor is wired to a dummy manager. Reads return empty results,
writes are no-ops. This keeps a content model usable even when an optional
relation's target isn't enabled in the project.

.. code-block:: python

    blog_post.optional_relation.all()       # → []
    blog_post.optional_relation.add(thing)  # no-op, no error

Accessing Relations
-------------------

The forward and reverse accessors return the same manager interface:

.. code-block:: python

    model.accessor.add(obj1, obj2)
    model.accessor.remove(obj1)
    model.accessor.clear()
    model.accessor.all()        # QuerySet
    model.accessor.filter(...)  # QuerySet — chain on top
    model.accessor.count()
    model.accessor.exists()

See Also
--------

- :doc:`../how-to/m2m_relations` - Practical implementation guide
- :doc:`../tutorials/model_with_m2m` - Step-by-step tutorial
- :doc:`../reference/index` - API reference
