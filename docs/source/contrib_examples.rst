Contrib examples
================

``djangocms-custom-content`` ships optional example apps under
``djangocms_custom_content.contrib``. They are intended as small, readable starting
points that demonstrate typical patterns:

- model-based content
- Django admin registration
- django CMS plugins for rendering
- simple "featured" / list-style plugins

Available modules
-----------------

- ``djangocms_custom_content.contrib.people``
- ``djangocms_custom_content.contrib.services``
- ``djangocms_custom_content.contrib.categories``
- ``djangocms_custom_content.contrib.blog``

Enabling them
-------------

Add one or more modules to ``INSTALLED_APPS`` and run migrations.

.. code-block:: python

    INSTALLED_APPS = [
        ...,
        "djangocms_custom_content",
        "djangocms_custom_content.contrib.people",
        "djangocms_custom_content.contrib.services",
        "djangocms_custom_content.contrib.categories",
        "djangocms_custom_content.contrib.blog",
        ...,
    ]

.. code-block:: bash

    python manage.py migrate

M2M Relations Example
---------------------

The ``people`` contrib module demonstrates the ``m2m_relations`` feature. It defines
a many-to-many relationship between ``Person`` profiles and ``BlogPost`` objects:

.. code-block:: python

    # In djangocms_custom_content/contrib/people/models.py
    class PersonContent(AbstractCustomContent):
        person = models.ForeignKey(Person, on_delete=models.CASCADE)
        # ... other fields ...

        class CMSConfig:
            m2m_relations = [("author_set", "djangocms_custom_content_blog.BlogPost")]

    # This line creates the relation model
    PersonRelation = custom_relation_factory(PersonContent)

This allows you to:

.. code-block:: python

    # Query all PersonContent objects that authored a blog post
    blog_post = BlogPost.objects.first()
    authors = blog_post.author_set.all()

    # Add a person as an author to a blog post
    blog_post.author_set.add(person_content)

    # Remove a person from a blog post
    blog_post.author_set.remove(person_content)

For more information on ``m2m_relations``, see the
:doc:`creating_custom_models` guide.
