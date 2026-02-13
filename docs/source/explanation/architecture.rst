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

M2M Relations Use Generic FK
----------------------------

Generic foreign keys allow flexible relationships:

.. code-block:: python

    class PersonRelation(AbstractCustomRelation):
        instance = ForeignKey(PersonContent)        # Which person
        content_type = ForeignKey(ContentType)      # What model type
        object_id = PositiveIntegerField()          # Which object
        related_field_name = CharField()             # "authors", "contributors", etc.

This single model stores relationships to ANY Django model without FK hardcoding.

See Also
--------

- :doc:`relationships` - How M2M works internally
