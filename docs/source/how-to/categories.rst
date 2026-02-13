Using the contrib.categories module
===================================

Flexible category system for organizing content.

Installation
-----------

.. code-block:: python

    INSTALLED_APPS = [
        "djangocms_custom_content",
        "djangocms_custom_content.contrib.categories",
    ]

.. code-block:: bash

    python manage.py migrate

Models
------

**Category** - Groups all language versions of a category
**CategoryContent** - Language-specific category information

Fields: ``title``, ``slug``, ``description``

Usage
-----

.. code-block:: python

    from djangocms_custom_content.contrib.categories.models import Category, CategoryContent

    category = Category.objects.create()
    CategoryContent.objects.create(
        category=category,
        language="en",
        title="Technology",
        slug="technology",
        description="Tech-related content",
    )

Linking to content:

.. code-block:: python

    # In your content model
    class CMSConfig:
        m2m_relations = [("categories", "blog.BlogPost")]

    # Use it
    post = BlogPost.objects.first()
    post.categories.all()

Plugins
-------

- ``CategoryList`` - Display all categories
- ``CategoryTeaser`` - Display a single category

Admin
-----

Registered with search by title and slug.

See Also
--------

- :doc:`../how-to/m2m_relations` - Add categories to your models
