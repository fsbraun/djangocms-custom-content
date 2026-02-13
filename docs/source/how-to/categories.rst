Using the contrib.categories module
===================================

Flexible category system for organizing content using the ``relate_to`` configuration.

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

**FlatCategory** - A simple category model (inherits from ``AbstractCustomContent``)

Fields: ``title``, ``slug``, ``is_featured``

The ``FlatCategory`` model uses the ``relate_to`` configuration to automatically add a ``categories`` accessor to ``BlogPost``:

.. code-block:: python

    class CMSConfig:
        relate_to = [("categories", "djangocms_custom_content_blog.BlogPost")]

Usage
-----

Create a category:

.. code-block:: python

    from djangocms_custom_content.contrib.categories.models import FlatCategory

    category = FlatCategory.objects.create(
        title="Technology",
        slug="technology",
        is_featured=True,
    )

Link categories to blog posts:

.. code-block:: python

    from djangocms_custom_content.contrib.blog.models import BlogPost

    blog_post = BlogPost.objects.first()
    
    # Add a category
    blog_post.categories.add(category)
    
    # Get all categories
    categories = blog_post.categories.all()
    
    # Remove a category
    blog_post.categories.remove(category)
    
    # Clear all categories
    blog_post.categories.clear()

Plugins
-------

- ``FlatCategoryList`` - Display all categories

Admin
-----

``FlatCategory`` is registered with search by title and slug.

In Templates
~~~~~~~~~~~~

.. code-block:: django

    <!-- Display categories linked to a blog post -->
    {% for category in blog_post.categories.all %}
        <a href="#" class="category" data-featured="{{ category.is_featured }}">
            {{ category.title }}
        </a>
    {% endfor %}

    <!-- Filter featured categories only -->
    {% for category in blog_post.categories.all %}
        {% if category.is_featured %}
            <span class="featured-category">{{ category.title }}</span>
        {% endif %}
    {% endfor %}

See Also
--------

- :doc:`../how-to/m2m_relations` - Learn about ``relate_to`` and ``invite_m2m_relations``
- :doc:`../explanation/relationships` - How M2M relations work
