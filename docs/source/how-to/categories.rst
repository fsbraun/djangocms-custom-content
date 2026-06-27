Using the contrib.categories module
===================================

Flexible category system for organizing content, used as a target of a
:class:`~djangocms_custom_content.relations.RelationField`.

Installation
------------

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

``FlatCategory`` itself declares no relations. Instead, ``BlogPost`` (the
grouper) opts in by declaring a ``RelationField`` that targets ``FlatCategory``
and invites a reverse ``blog_posts`` accessor onto it (see
``contrib/blog/models.py``):

.. code-block:: python

    class BlogPost(AbstractCustomGrouper):
        categories = RelationField(
            "djangocms_custom_content_categories.FlatCategory",
            related_name="blog_posts",
        )

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

The reverse accessor invited by ``related_name="blog_posts"`` lets you go the
other way without ``FlatCategory`` declaring anything:

.. code-block:: python

    category = FlatCategory.objects.first()
    category.blog_posts.all()  # BlogPost groupers in this category

Plugins
-------

- ``CategoryListPlugin`` ("Category list", model ``FlatCategoryList``) -
  Display categories, optionally featured-only and limited

Admin
-----

``FlatCategory`` has **no grouper**, so it is registered with a plain
``admin.ModelAdmin`` (search by title and slug) — not the grouper admin.

What this app demonstrates
--------------------------

``FlatCategory`` is a **grouper-less content model used as a relation target**:
it opts out of versioning and app hooks, yet ``BlogPost`` can still relate to it
and gets a ``blog_posts`` reverse accessor on it for free.

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

- :doc:`../how-to/m2m_relations` - Declaring ``RelationField`` relations
- :doc:`../explanation/relationships` - How grouper relations work
