How-To: Set Up Many-to-Many Relations (m2m_relations)
====================================================

M2M relations connect your content objects to other Django models using ``custom_relation_factory()`` and ``CMSConfig.m2m_relations``.

Creating a Relation Model
--------------------------

.. code-block:: python

    from djangocms_custom_content.models import (
        AbstractCustomContent,
        custom_relation_factory,
    )

    class Tag(AbstractCustomContent):
        """A tag that can be attached to content."""
        tag = models.ForeignKey("my_app.TagGrouper", on_delete=models.CASCADE)
        name = models.CharField(max_length=100)

        class CMSConfig:
            # Add 'tags' accessor to Article and BlogPost
            m2m_relations = [
                ("tags", "my_app.Article"),
                ("tags", "my_app.BlogPost"),
            ]

        def __str__(self):
            return self.name

    # Create the relation model automatically
    TagRelation = custom_relation_factory(Tag)

Key points:

- Inherit from ``AbstractCustomContent``
- ``m2m_relations`` is a list of tuples: ``(accessor_name, "app_label.ModelName")``
- Call ``custom_relation_factory()`` to generate the relation storage model
- Use model strings to avoid circular imports

Configuration Options
---------------------

.. code-block:: python

    class CMSConfig:
        m2m_relations = [
            # Simple tuple format
            ("categories", "my_app.Article"),
            ("tags", "my_app.BlogPost"),
            # Or dynamically via property
        ]

You can also define ``m2m_relations`` as a property for dynamic configuration:

.. code-block:: python

    from django.apps import apps

    class CMSConfig:
        @property
        def m2m_relations(self):
            relations = []
            if apps.is_installed("my_optional_app"):
                relations.append(("tags", "my_optional_app.Article"))
            return relations

Using the Accessor
------------------

The accessor works like Django's ``ManyToManyField``:

.. code-block:: python

    article = Article.objects.first()
    tag = Tag.objects.first()

    # Available methods
    article.tags.add(tag)
    article.tags.remove(tag)
    article.tags.clear()
    article.tags.all()
    article.tags.filter(name="Django")
    article.tags.count()
    article.tags.exists()

In Templates
~~~~~~~~~~~~

.. code-block:: django

    {% for tag in article.tags.all %}
        <span class="tag">{{ tag.name }}</span>
    {% endfor %}

Common Patterns
---------------

Multiple accessors from one model:

.. code-block:: python

    class Category(AbstractCustomContent):
        category = models.ForeignKey("my_app.CategoryGrouper", on_delete=models.CASCADE)
        name = models.CharField(max_length=100)

        class CMSConfig:
            m2m_relations = [
                ("primary_category", "my_app.Article"),
                ("secondary_categories", "my_app.Article"),
                ("categories", "my_app.BlogPost"),
            ]

Troubleshooting
---------------

**"Cannot find model: app.Model"** - Check the model name in ``m2m_relations`` is correct.

**Accessor not appearing** - Ensure you called ``custom_relation_factory(YourContentModel)``.

**Circular imports** - Always use strings for model references: ``"app_label.ModelName"``.

**No migrations** - Run ``python manage.py makemigrations`` and ``migrate``.

See Also
--------

- :doc:`../reference/index` - API reference
- :doc:`../explanation/relationships` - How M2M relations work
