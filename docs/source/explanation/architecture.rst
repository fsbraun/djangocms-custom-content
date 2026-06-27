Architecture
============

Core Design: Grouper + Content Pattern
--------------------------------------

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

- **Multilingual by default** - Add language by creating new Content object
- **Version history** - Old Content objects remain in database
- **Clean separation** - Grouper is identity, Content is presentation
- **Efficient** - One query per language

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
