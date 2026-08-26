Architecture
============

Core Design: Grouper + Content Pattern
--------------------------------------

This framework adopts django CMS's own **content object** pattern. In short, an
editable item is split into a *grouper* (stable identity) and one or more
*content* rows (the editable, per-language, versioned state); foreign keys point
at the grouper so they survive translations and version copies. For the full
rationale, see the upstream explanation,
`Content objects <https://docs.django-cms.org/en/latest/explanation/content_objects.html>`_.

djangocms-custom-content uses a two-model pattern:

**Grouper** - One per item (e.g., Article)
  - Persistent identity
  - Minimal data
  - Links to many Content objects

**Content** - One per language (e.g., ArticleContent)
  - Language-specific data (title, body)
  - Version history automatically supported
  - Quick language switching

Why This Design?

- **Multilingual by default** - Each language is a Content row pointing at the
  same grouper.
- **Version history** - Versioning copies the Content row (new primary key);
  the grouper is untouched.
- **Stable references** - Because foreign keys and
  :class:`~djangocms_custom_content.relations.RelationField` relations target the
  *grouper*, not a Content row, they survive translations and version copies.
- **Cheap reads** - ``get_content()`` issues a single query and caches every
  language of the grouper, so subsequent language lookups hit the cache rather
  than the database.

Example:

.. code-block:: python

    # One Article (grouper)
    article = Article.objects.create(name="My Article")

    # Multiple ArticleContent (per language)
    content_en = ArticleContent.objects.create(
        article=article,
        language="en",
        title="English Title",
        body="English content..."
    )

    content_de = ArticleContent.objects.create(
        article=article,
        language="de",
        title="German Title",
        body="German content..."
    )

Reading content: ``get_content`` vs ``get_admin_content``
---------------------------------------------------------

A grouper exposes two accessors, and the difference matters when versioning is
enabled:

- :meth:`~djangocms_custom_content.models.AbstractCustomGrouper.get_content` -
  the **published** content for a language (defaults to the current language).
  This is what you use in public templates.
- :meth:`~djangocms_custom_content.models.AbstractCustomGrouper.get_admin_content` -
  the **latest** content, including drafts, optimised for admin listings.

.. code-block:: python

    article.get_content(language="en")        # published — for the site
    article.get_admin_content(language="en")  # latest draft — for the admin

Because relation accessors return *groupers* (e.g. ``post.authors.all()`` yields
``Person`` groupers), reach their displayable fields through one of these
accessors: ``person.get_admin_content().name``.

Rendering: template defaults
----------------------------

Content models render without any wiring, thanks to a naming convention. By
default a content object looks for:

.. code-block:: text

    <app_label>/<modelname>_detail.html

So ``ArticleContent`` in an app called ``my_content`` renders from
``my_content/articlecontent_detail.html``, and the object is available in that
template under its **model name** (``articlecontent``). The ``_detail`` part is
:attr:`~djangocms_custom_content.models.AbstractCustomContent.template_name_suffix`,
and the same default serves both the app-hook detail view and the frontend
editor — one template covers both.

All four bundled contrib apps follow this convention rather than overriding it,
so ``BlogPostContent`` in ``djangocms_custom_content.contrib.blog`` renders from
``djangocms_custom_content_blog/blogpostcontent_detail.html``.

Need a different template? Override
:meth:`~djangocms_custom_content.models.AbstractCustomContent.get_template`:

.. code-block:: python

    class ArticleContent(AbstractCustomContent):
        def get_template(self):
            return "my_content/article.html"

The :doc:`../how-to/apphooks` guide spells out the full contract — which context
variables each render path provides, and how an override interacts with the
app-hook view.

.. _overriding-a-bundled-template:

Overriding a bundled template
-----------------------------

Every template the contrib apps ship lives inside the app that uses it, in a
directory named after that app's **label**:

.. code-block:: text

    contrib/blog/templates/djangocms_custom_content_blog/
    contrib/categories/templates/djangocms_custom_content_categories/
    contrib/people/templates/djangocms_custom_content_people/
    contrib/services/templates/djangocms_custom_content_services/

Because the label prefixes the path, nothing a bundled app ships can collide
with a template of your own — and overriding one is the ordinary Django move:
put a file at the same path in a directory that the loader reaches first,
usually your project's ``DIRS`` entry.

.. code-block:: text

    myproject/templates/djangocms_custom_content_blog/blog_post_teaser.html

That replaces the bundled blog teaser everywhere the plugin renders, without
touching the package or subclassing the plugin.

Not everything needs a grouper
------------------------------

A content model becomes part of a grouper/content pair only when it declares a
foreign key to an :class:`~djangocms_custom_content.models.AbstractCustomGrouper`.
Skip that foreign key and you get a simpler, perfectly valid shape — like the
bundled ``FlatCategory`` — that opts out of versioning, app hooks and the grouper
admin, yet can still be used as a relation target. Start simple; add a grouper
only when you actually need versions or languages.

Relations Are Grouper-Anchored
------------------------------

Relations between content are declared with
:class:`~djangocms_custom_content.relations.RelationField` on a **grouper**, and
read like a ``ManyToManyField``:

.. code-block:: python

    from djangocms_custom_content.relations import RelationField

    class BlogPost(AbstractCustomGrouper):
        authors = RelationField("people.Person", related_name="authored_posts", ordered=True)

Each relation gets its own through table with a concrete ``source`` foreign key
to the owning grouper and a ``GenericForeignKey`` ``target``, so one relation can
point at groupers of any type without hardcoding FKs:

.. code-block:: python

    # Conceptual shape of the generated through model
    class BlogPostAuthorsRelation(OrderedCustomRelation):
        source = ForeignKey(BlogPost)               # the owning grouper
        content_type = ForeignKey(ContentType)      # which target type
        object_id = PositiveIntegerField()          # which target grouper
        target = GenericForeignKey(...)             # resolved target
        order = PositiveIntegerField()              # only when ordered=True

Because edges store the **grouper's** stable primary key, they survive
djangocms-versioning version copies untouched.

See Also
--------

- :doc:`relationships` - How relations work internally
