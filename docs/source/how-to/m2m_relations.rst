Set Up Many-to-Many Relations
=============================

djangocms-custom-content exposes a single declarative API for many-to-many
relationships between custom content models: ``CMSConfig.m2m``. One entry
declares both directions; the framework auto-generates the through-table and
wires forward and reverse accessors for you.

The Declaration
---------------

Add an ``m2m`` list to your content model's ``CMSConfig``. Each entry is a
2- or 3-tuple:

.. code-block:: python

    class BlogPostContent(AbstractCustomContent):
        post = models.ForeignKey("blog.BlogPost", on_delete=models.CASCADE)
        title = models.CharField(max_length=200)

        class CMSConfig:
            m2m = [
                ("authors", "people.Person"),                  # auto reverse
                ("tags", "tags.Tag", "blog_posts"),            # explicit reverse name
                ("featured", "promo.Promo", None),             # no reverse accessor
            ]

The tuple positions are:

1. **Forward accessor name** — installed on the declarer's grouper (or the
   declarer itself if it has no grouper).
2. **Target label** — ``"app_label.ModelName"`` of the model being related to.
3. **Reverse accessor name** (optional) — installed on the target. Omit to
   auto-derive (``"{owner_model_name}_set"``). Pass ``None`` to suppress the
   reverse accessor.

What the framework does for you
-------------------------------

For each content model that declares ``m2m``, the framework generates a single
through-model named ``{ContentModelName}Relation`` in the declaring app. Its
schema is:

* ``instance`` — ForeignKey to the declarer's grouper (or to the content model
  itself if there is no grouper).
* ``content_type`` + ``object_id`` (+ ``content_object`` GFK) — point at the
  target object.
* ``relation_name`` — distinguishes multiple relations that share the same
  through-table.

You **do not** need to subclass ``AbstractCustomRelation`` or call any factory
helper. ``makemigrations`` picks up the generated model just like any other.

Usage
-----

.. code-block:: python

    blog_post = BlogPost.objects.first()        # grouper
    person = Person.objects.first()             # target grouper

    # Forward accessor on the grouper
    blog_post.authors.add(person)
    list(blog_post.authors.all())               # → [<Person>]

    # Auto-derived reverse accessor on the target grouper
    list(person.blogpost_set.all())             # → [<BlogPost>]

Manager interface
-----------------

Both forward and reverse accessors return the same manager:

.. code-block:: python

    model.accessor.add(obj1, obj2)
    model.accessor.remove(obj1)
    model.accessor.clear()
    model.accessor.all()        # QuerySet of related objects
    model.accessor.filter(...)  # QuerySet — chain on top
    model.accessor.count()
    model.accessor.exists()

Where the accessors land
------------------------

The forward accessor (``"authors"`` above) is installed on the **declarer's
grouper** if it has one, otherwise on the content model itself. Because the
through-model's FK points at the grouper, relations are language-independent
by default — adding an author to a blog post associates them with all language
versions at once.

If a content model has no grouper, the relation is owned by the content model
directly, and the auto-reverse name is ``"{contentmodel}_set"`` instead.

Multiple relations to the same target
-------------------------------------

A content model can declare several relations to the same target model. The
``relation_name`` column keeps them independent:

.. code-block:: python

    class BlogPostContent(AbstractCustomContent):
        class CMSConfig:
            m2m = [
                ("authors", "people.Person", "authored"),
                ("editors", "people.Person", "edited"),
            ]

.. code-block:: python

    blog_post.authors.add(alice)
    blog_post.editors.add(bob)

    list(blog_post.authors.all())   # [alice]
    list(blog_post.editors.all())   # [bob]

    list(alice.authored.all())      # [blog_post]
    list(bob.edited.all())          # [blog_post]

Auto reverse name is one per owner — if you declare two relations to the same
target without explicit reverse names, both will try to install
``"{owner}_set"`` on the target and the second one wins. In that case give at
least one of them an explicit reverse name (or pass ``None`` to suppress).

Targets that are not installed
------------------------------

If a relation's target model is not present in ``INSTALLED_APPS`` (for example
an optional contrib app), the forward accessor is wired to a dummy manager
that returns empty results and silently accepts ``add()``/``remove()`` calls.
This lets a content model declare optional relations without crashing when
the optional app isn't enabled.

In templates
------------

.. code-block:: django

    {% for author in blog_post.authors.all %}
        <strong>{{ author.get_admin_content.name }}</strong>
    {% endfor %}

    {% for category in blog_post.categories.all %}
        <span class="category">{{ category.title }}</span>
    {% endfor %}

See Also
--------

- :doc:`../reference/index` - API reference
- :doc:`../explanation/relationships` - Why and how it works under the hood
- :doc:`../tutorials/model_with_m2m` - Step-by-step tutorial
