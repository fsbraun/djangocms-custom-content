Using the contrib.categories module
===================================

Flexible category system for organizing content.

Installation
-----------

.. code-block:: python

    INSTALLED_APPS = [
        "djangocms_custom_content",
        "djangocms_custom_content.contrib.blog",
        "djangocms_custom_content.contrib.categories",
    ]

.. code-block:: bash

    python manage.py migrate

Models
------

**FlatCategory** - A simple category model (inherits from ``AbstractCustomContent``)

Fields: ``title``, ``slug``, ``is_featured``.

The relation between ``BlogPostContent`` and ``FlatCategory`` is declared
**on the blog side** via ``CMSConfig.m2m``:

.. code-block:: python

    class BlogPostContent(AbstractCustomContent):
        class CMSConfig:
            m2m = [
                ("categories", "djangocms_custom_content_categories.FlatCategory"),
            ]

That single declaration installs ``BlogPost.categories`` (forward, on the
grouper) and the auto-named reverse ``FlatCategory.blogpost_set``.

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

    # Forward — manage categories from the blog post side
    blog_post.categories.add(category)
    list(blog_post.categories.all())
    blog_post.categories.remove(category)
    blog_post.categories.clear()

    # Reverse — list blog posts attached to a category
    list(category.blogpost_set.all())

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

- :doc:`../how-to/m2m_relations` - The full ``CMSConfig.m2m`` reference
- :doc:`../explanation/relationships` - How M2M relations work
