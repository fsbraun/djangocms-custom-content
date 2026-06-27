========================
djangocms-custom-content
========================

|PyPiVersion| |PyVersion| |DjVersion| |CmsVersion| |Coverage|

**Custom content types for django CMS — without the boilerplate.**

Building a custom content type in django CMS by hand means wiring up a grouper,
versioning, a grouper admin, frontend editing, an app hook and migrations
yourself. ``djangocms-custom-content`` does all of that — you write the model.

Write this…
===========

.. code-block:: python

    from django.db import models
    from djangocms_custom_content.models import AbstractCustomGrouper, AbstractCustomContent

    class Article(AbstractCustomGrouper):
        pass

    class ArticleContent(AbstractCustomContent):
        article = models.ForeignKey(Article, on_delete=models.CASCADE)
        language = models.CharField(max_length=10)
        slug = models.SlugField()
        title = models.CharField(max_length=200)
        body = models.TextField()

        class CMSConfig:
            enable_versioning = True
            enable_frontend_editing = True
            apphook = True

…and that model (plus a few lines of grouper admin) gives you, for free:

* per-language draft/publish version history
* frontend, double-click editing inside the page
* a detail view at a clean URL, with ``get_absolute_url()`` injected
* a grouper admin to create and manage content

Want related content? Add **one line** to the grouper —
``authors = RelationField("people.Person", ordered=True)`` — and the admin renders
a sortable autocomplete, anchored to the grouper so the link survives every new
version.

.. note::

    **Status: 0.5 — usable, pre-1.0.** The relations system is a ground-up rewrite
    and the framework runs the bundled apps and test suite, but APIs may still
    shift before 1.0. Feedback and bug reports are very welcome.

Why you'll want it
==================

* **Write the model, skip the plumbing** — versioning, grouper admin, frontend
  editing, app hooks and migrations are handled.
* **Relations that survive versioning** — related content is anchored to the
  grouper, so links don't break when a new version is published.
* **Sortable related-content widgets, free** — every relation renders as an
  autocomplete multi-select in the admin, drag-sortable when ordered.
* **Relate to anything without touching it** — generic relations need no foreign
  key or migration on the target model.
* **Multi-language & versioned** — per-language draft/publish history per content
  model.
* **Batteries included** — bundled blog, people, categories and services apps to
  use as-is or copy and adapt.
* **django CMS 5.0+** — supports django CMS 5.0 and later and Django 5.2 to 6.0.

See it work in two minutes
==========================

Don't build anything yet — turn on a bundled example and click around first::

    pip install djangocms-custom-content

Add the blog (plus the apps it relates to) to ``INSTALLED_APPS`` and migrate::

    INSTALLED_APPS = [
        # ... django CMS and its dependencies ...
        "djangocms_custom_content",
        "djangocms_custom_content.contrib.people",
        "djangocms_custom_content.contrib.categories",
        "djangocms_custom_content.contrib.blog",
    ]

    python manage.py migrate

That's it — a versioned, frontend-editable blog in the admin, with sortable
authors and categories relations and ready-to-place CMS plugins, no models
written. Then build your own by following the documentation:

https://djangocms-custom-content.readthedocs.io/

Contrib examples
================

This package ships optional, small example apps under ``djangocms_custom_content.contrib``.
They are quick starting points (models + admin + django CMS plugins) you can enable
as-is or copy and adapt:

* ``djangocms_custom_content.contrib.people``: ``Person`` grouper/content (a
  versioned grouper without a language field) + "Person teaser" plugin
* ``djangocms_custom_content.contrib.categories``: ``FlatCategory`` — a
  grouper-less taxonomy used as a relation target + "Category list" plugin
* ``djangocms_custom_content.contrib.services``: a plain ``Service`` model +
  "Service teaser" and "Featured services" plugins
* ``djangocms_custom_content.contrib.blog``: blog posts with ordered ``authors``
  and ``categories`` relations + "Blog post" teaser plugin

To enable one (or more), add the module(s) to ``INSTALLED_APPS`` and run migrations::

    INSTALLED_APPS = [
        ...,
        'djangocms_custom_content',
        'djangocms_custom_content.contrib.people',  # contrib are optional
        'djangocms_custom_content.contrib.services',
        'djangocms_custom_content.contrib.categories',
        'djangocms_custom_content.contrib.blog',
        ...,
    ]

    python manage.py migrate

Contributing
============

Contributions are welcome! Please feel free to submit a Pull Request.

License
=======

This project is licensed under the BSD-3-Clause License.


.. |PyPiVersion| image:: https://img.shields.io/pypi/v/djangocms-custom-content?style=flat-square
    :target: https://pypi.python.org/pypi/djangocms-custom-content
    :alt: Latest PyPI version

.. |PyVersion| image:: https://img.shields.io/pypi/pyversions/djangocms-custom-content?style=flat-square
    :target: https://pypi.python.org/pypi/djangocms-custom-content
    :alt: Python versions

.. |DjVersion| image:: https://img.shields.io/pypi/frameworkversions/django/djangocms-custom-content?style=flat-square
    :target: https://pypi.python.org/pypi/djangocms-custom-content
    :alt: Django versions

.. |CmsVersion| image:: https://img.shields.io/pypi/frameworkversions/django-cms/djangocms-custom-content?style=flat-square
    :target: https://pypi.python.org/pypi/djangocms-custom-content
    :alt: django CMS versions

.. |Coverage| image:: https://codecov.io/gh/fsbraun/djangocms-custom-content/graph/badge.svg?token=GESjKzHSXl&style=flat-square
    :target: https://codecov.io/gh/fsbraun/djangocms-custom-content
