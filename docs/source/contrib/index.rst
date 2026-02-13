Contrib Modules
===============

Pre-built models and patterns you can use out of the box.

.. toctree::
   :maxdepth: 2

   people
   blog
   categories
   services

The contrib modules provide ready-to-use models for common content types.

Quick Overview
--------------

**People Module**

Author and contributor management with generic M2M relations to blog posts.

- Models: ``Person``, ``PersonContent``
- Relations: Authors on ``BlogPost``
- Use case: Blog with multiple authors

**Blog Module**

Blog post management with featured content support.

- Models: ``BlogPost``, ``BlogPostContent``
- Relations: None by default
- Use case: Running a blog on your site

**Categories Module**

Hierarchical category/tag support.

- Models: ``Category``, ``CategoryContent``
- Relations: Link to any content
- Use case: Organizing content into categories

**Services Module**

Service or product management.

- Models: ``Service``, ``ServiceContent``
- Relations: None by default
- Use case: Listing services or products

Installation
-----------

Add to ``INSTALLED_APPS`` in ``settings.py``:

.. code-block:: python

    INSTALLED_APPS = [
        # ... other apps ...
        "djangocms_custom_content",
        "djangocms_custom_content.contrib.people",
        "djangocms_custom_content.contrib.blog",
        "djangocms_custom_content.contrib.categories",
        "djangocms_custom_content.contrib.services",
    ]

Then run migrations:

.. code-block:: bash

    python manage.py migrate

See Also
--------

- :doc:`people` - People/authors module
- :doc:`blog` - Blog module
- :doc:`categories` - Categories module
- :doc:`services` - Services module
- :doc:`../tutorials/blog_example` - Blog example tutorial
- :doc:`../how-to/m2m_relations` - M2M relations guide
