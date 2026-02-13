Creating Custom Models
======================

This package is designed to be extended with your own Django models.

Minimal Workflow
----------------

1. Create a Django app (e.g. ``my_content``)
2. Add to ``INSTALLED_APPS``
3. Define content model(s) inheriting from ``AbstractCustomContent``
4. Create CMS plugins to render the content
5. Create templates
6. Run ``makemigrations`` and ``migrate``

Basic Example
-------------

Model:

.. code-block:: python

    from djangocms_custom_content.models import AbstractCustomContent

    class Article(AbstractCustomContent):
        title = models.CharField(max_length=200)
        body = models.TextField()

Plugin:

.. code-block:: python

    from cms.plugin_base import CMSPluginBase
    from cms.plugin_pool import plugin_pool

    @plugin_pool.register_plugin
    class ArticlePlugin(CMSPluginBase):
        name = "Article"
        render_template = "article.html"

        def render(self, context, instance, placeholder):
            return {**context, "article": instance}

Template:

.. code-block:: django

    <article>
        <h3>{{ article.title }}</h3>
        <p>{{ article.body }}</p>
    </article>

Many-to-Many Relations
---------------------

Connect content models to other models using ``m2m_relations``:

.. code-block:: python

    from djangocms_custom_content.models import (
        AbstractCustomContent,
        custom_relation_factory
    )

    class Person(AbstractCustomContent):
        full_name = models.CharField(max_length=200)

        class CMSConfig:
            m2m_relations = [
                ("authors", "blog.BlogPost"),
            ]

    # Required call
    PersonRelation = custom_relation_factory(Person)

Usage:

.. code-block:: python

    post = BlogPost.objects.first()
    post.authors.all()  # Get all related Person objects
    post.authors.add(person)  # Add a Person
    post.authors.remove(person)  # Remove a Person

Key Points
----------

- Always inherit from ``AbstractCustomContent`` or ``AbstractCustomGrouper``
- Call ``custom_relation_factory()`` if using ``m2m_relations``
- Use model strings in ``m2m_relations`` to avoid circular imports
- Register plugins with ``plugin_pool.register_plugin``
- Create templates for your plugins to display content

See Also
--------

- :doc:`tutorials/basic_setup` - Installation tutorial
- :doc:`tutorials/blog_example` - Complete blog example
- :doc:`reference/index` - API reference
