Run without django CMS
======================

Reusable Django applications can use ``djangocms-custom-content`` without
forcing projects that install them to install django CMS. The model bases,
mixins and relation system depend on Django, but do not import django CMS.

Declare the reusable application's dependency normally:

.. code-block:: toml

    [project]
    dependencies = [
        "Django>=5.2",
        "djangocms-custom-content",
    ]

A project that does not use django CMS adds the reusable app and the custom
content framework to ``INSTALLED_APPS`` without adding ``cms``:

.. code-block:: python

    INSTALLED_APPS = [
        "django.contrib.contenttypes",  # required by RelationField
        "djangocms_custom_content",
        "my_reusable_app",
    ]

Models use the same API in CMS and non-CMS projects:

.. code-block:: python

    from django.db import models

    from djangocms_custom_content.models import (
        AbstractCustomContent,
        AbstractCustomGrouper,
    )
    from djangocms_custom_content.relations import RelationField


    class Topic(AbstractCustomGrouper):
        name = models.CharField(max_length=100)


    class Article(AbstractCustomGrouper):
        topics = RelationField(Topic, related_name="articles")


    class ArticleContent(AbstractCustomContent):
        article = models.ForeignKey(Article, on_delete=models.CASCADE)
        language = models.CharField(max_length=8)
        title = models.CharField(max_length=200)

The grouper/content accessors and relations remain available:

.. code-block:: python

    article.get_content("en")
    article.topics.add(topic)
    article.topics.all()
    topic.articles.all()

Without django CMS, ``admin_manager`` is an ordinary all-content manager and
there is no draft/published distinction. The following CMS features are not
available:

- placeholders;
- frontend editing and CMS toolbar integration;
- generated CMS app hooks;
- CMS plugins;
- django CMS versioning integration.

Keep optional CMS integration in modules that django CMS discovers itself,
e.g., ``cms_config.py`` and ``cms_plugins.py``. Do not import those modules
from the reusable application's ``models.py``, ``apps.py`` or ``__init__.py``.
When django CMS is installed, it imports them during normal discovery and
``djangocms-custom-content`` adds the real placeholder relation and CMS-aware
admin manager to each content model. Without django CMS, those modules are never
loaded.

An inner ``CMSConfig`` declaration on a content model is harmless in a non-CMS
project: it is a plain Python class and is read only when django CMS performs
configuration.

If the reusable models already inherit from another Django model base, use the
framework mixins as described in :ref:`mixin-model-bases`.
