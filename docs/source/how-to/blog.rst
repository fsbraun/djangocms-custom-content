Using the contrib.blog module
=============================

Complete blog system with posts, featured posts, and versioning.

Installation
------------

.. code-block:: python

    INSTALLED_APPS = [
        "djangocms_custom_content",
        "djangocms_custom_content.contrib.blog",
    ]

.. code-block:: bash

    python manage.py migrate

Models
------

**BlogPost** - Groups all language versions of a blog post. Declares two
grouper-to-grouper relations via :class:`~djangocms_custom_content.relations.RelationField`:
``authors`` (ordered, to ``people.Person``) and ``categories``
(to ``categories.FlatCategory``).

**BlogPostContent** - Language-specific post content

Content fields: ``title``, ``slug``, ``excerpt``, ``body``, ``is_featured``,
``published_at``, ``language``

Usage
-----

.. code-block:: python

    from djangocms_custom_content.contrib.blog.models import BlogPost, BlogPostContent

    post = BlogPost.objects.create()
    BlogPostContent.objects.create(
        post=post,
        language="en",
        title="My First Post",
        slug="my-first-post",
        excerpt="Short summary...",
        body="Full content...",
    )

    # Access by language
    english_version = post.get_content(language="en")

    # Get featured posts
    featured = BlogPostContent.objects.filter(is_featured=True)

Plugins
-------

- ``BlogPostTeaserPlugin`` ("Blog post") - Display a single selected post

Admin
-----

``BlogPostAdmin`` is a ``GrouperModelAdmin`` (see :doc:`admin`) with
``content__``-prefixed list display and search, and it renders the ``authors``
and ``categories`` relations as autocomplete widgets.

What this app demonstrates
--------------------------

The blog is the reference example for the relations system: it declares **both**
an *ordered* relation (``authors`` → ``Person``, drag-sortable in the admin) and
an *unordered* one (``categories`` → ``FlatCategory``), on a content model that
is **per-language versioned** (it has a ``language`` field) and frontend-editable.

See Also
--------

- :doc:`../how-to/m2m_relations` - How ``authors`` and ``categories`` relations work
- :doc:`../how-to/people` - The ``Person`` model used as authors
- :doc:`../how-to/categories` - The ``FlatCategory`` model used as categories
