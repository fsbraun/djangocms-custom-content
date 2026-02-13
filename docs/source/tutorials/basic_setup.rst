Installation and Example
========================

Install djangocms-custom-content and create your first editable, versionable content model.

Prerequisites
-------------

- Django project with django CMS installed
- About 5 minutes

Step 1: Install the Package
----------------------------

Install djangocms-custom-content:

.. code-block:: bash

    pip install djangocms-custom-content

Step 2: Add to INSTALLED_APPS
-----------------------------

Add to your Django settings:

.. code-block:: python

    INSTALLED_APPS = [
        # ...
        "djangocms_custom_content",
    ]

Then run migrations:

.. code-block:: bash

    python manage.py migrate djangocms_custom_content

Step 3: Create a Django App
----------------------------

Create an app for your content:

.. code-block:: bash

    python manage.py startapp my_content

Add it to ``INSTALLED_APPS``:

.. code-block:: python

    INSTALLED_APPS = [
        # ...
        "djangocms_custom_content",
        "my_content",
    ]

Step 4: Create a Content Model
-------------------------------

Create ``my_content/models.py``:

.. code-block:: python

    from django.db import models
    from djangocms_custom_content.models import (
        AbstractCustomGrouper,
        AbstractCustomContent,
    )

    class Article(AbstractCustomGrouper):
        """Groups all language versions of an article."""
        pass

    class ArticleContent(AbstractCustomContent):
        """The editable article content."""
        article = models.ForeignKey(Article, on_delete=models.CASCADE)
        title = models.CharField(max_length=200)
        slug = models.SlugField()
        body = models.TextField()

        class CMSConfig:
            # Make editable in frontend and versionable
            editable = True
            versionable = True

        def __str__(self):
            return self.title

The ``CMSConfig`` class enables:

- ``enable_frontend_editing = True`` - Content can be edited on the frontend in django CMS
- ``enable_versioning = True`` - Track and manage multiple versions by language

Step 5: Register with Admin
----------------------------

Create ``my_content/admin.py``:

.. code-block:: python

    from django.contrib import admin
    from .models import Article, ArticleContent

    @admin.register(Article)
    class ArticleAdmin(admin.ModelAdmin):
        pass

    @admin.register(ArticleContent)
    class ArticleContentAdmin(admin.ModelAdmin):
        list_display = ("title", "language", "article")

Step 6: Run Migrations
----------------------

.. code-block:: bash

    python manage.py makemigrations my_content
    python manage.py migrate

Done!
-----

Your content model is now:

✅ Installed and configured
✅ Editable in the django CMS frontend
✅ Versionable by language
✅ Available in Django admin

Next Steps:

- :doc:`../how-to/m2m_relations` - Add relationships to other models
- :doc:`../explanation/architecture` - Understand the grouper/content pattern
- :doc:`blog_example` - Build a complete blog system
