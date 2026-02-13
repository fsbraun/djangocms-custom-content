Using the contrib.blog module
=============================

Complete blog system with posts, featured posts, and versioning.

Installation
-----------

.. code-block:: python

    INSTALLED_APPS = [
        "djangocms_custom_content",
        "djangocms_custom_content.contrib.blog",
    ]

.. code-block:: bash

    python manage.py migrate

Models
------

**BlogPost** - Groups all language versions of a blog post
**BlogPostContent** - Language-specific post content (title, body, excerpt)

Fields: ``title``, ``slug``, ``excerpt``, ``body``, ``is_featured``, ``published_at``

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

- ``BlogPostTeaser`` - Display a single featured post
- ``LatestBlogPosts`` - Display recent blog posts
- ``BlogPostList`` - Display all blog posts

Admin
-----

Registered with list display, filters, and search by title/slug.

Features
--------

- Multi-language support
- Featured post highlighting
- Publication date tracking
- Admin-friendly interface

See Also
--------

- :doc:`../tutorials/blog_example` - Complete blog tutorial
- :doc:`../how-to/m2m_relations` - Add authors using M2M relations
