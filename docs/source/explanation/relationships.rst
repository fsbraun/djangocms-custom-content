M2M Relationships Explained
===========================

How Generic M2M Works
---------------------

djangocms-custom-content uses Django's ContentType framework for flexible relationships.

**Storage Model**

.. code-block:: python

    class PersonRelation(AbstractCustomRelation):
        instance = ForeignKey(PersonContent)        # FK to the relation source
        content_type = ForeignKey(ContentType)      # Type of related model
        object_id = PositiveIntegerField()          # ID of related object
        related_field_name = CharField()             # Accessor name ("authors", etc.)

One table stores relationships to ANY Django model.

**Example Data**

.. code-block:: sql

    -- Person 5 is "author" of BlogPost 1
    INSERT INTO person_relation (instance_id, content_type_id, object_id, related_field_name)
    VALUES (5, 42, 1, "authors");

    -- content_type_id 42 = BlogPost

**Accessing Relations**

.. code-block:: python

    blog_post = BlogPost.objects.first()
    person = PersonContent.objects.first()

    # Add
    blog_post.author_set.add(person)

    # Get all
    authors = blog_post.author_set.all()

    # Behind the scenes, queries PersonRelation table

**Multiple Accessors**

Same relation model, different accessors:

.. code-block:: python

    class PersonContent(AbstractCustomContent):
        class CMSConfig:
            m2m_relations = [
                ("authors", "blog.BlogPost"),
                ("contributors", "blog.BlogPost"),
            ]

The ``related_field_name`` distinguishes them in the database.

Why This Design?
----------------

- **Reusable** - PersonContent relates to multiple models without code changes
- **Extensible** - Add new relations by updating CMSConfig
- **Scalable** - Works with hundreds of relation types
- **Generic** - Works with any Django model

See Also
--------

- :doc:`architecture` - Overall design
- :doc:`../how-to/m2m_relations` - Practical guide
- :doc:`../reference/index` - API reference
