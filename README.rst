========================
djangocms-custom-content
========================

|PyPiVersion| |PyVersion| |DjVersion| |CmsVersion| |Coverage|

Developer framework for integrating custom content models with django CMS.

Description
===========

``djangocms-custom-content`` provides a developer-friendly framework to quickly build
and integrate your own custom content models with django CMS.

It helps you define CMS-enabled custom models with minimal boilerplate. Depending on your
project needs, it can optionally add:

* apphooks for dedicated content sections/URLs
* frontend editable placeholders
* versioning support
* relationships to other content types or existing domain models

The package also includes ready-to-use CMS plugins for displaying custom content
items (e.g. detail/teaser views), as well as patterns for related and featured
content.

Features
========

* Fast setup for custom content models and CMS integration
* CMS plugins for rendering content, related content, and featured content
* Optional apphooks, versioning, and model relationships
* Compatible with django CMS 5.0 and later
* Support for Django 5.2 through 6.0
* Easy integration into existing django CMS projects

Installation
============

Install the package using pip::

    pip install djangocms-custom-content

Add it to your ``INSTALLED_APPS``::

    INSTALLED_APPS = [
        ...
        'djangocms_custom_content',
        ...
    ]

Run migrations::

    python manage.py migrate djangocms_custom_content

Usage
=====

This package is intended to be extended in your project:

* Define one or more custom content models.
* Register and configure the provided CMS integration (admin + plugins).
* Use the included plugins to place and render your content in placeholders.
* Optionally enable apphooks/versioning/relationships for richer content
    architectures.

The exact configuration depends on your project and the content types you build.

To learn how to build your own model-based content types with this framework, see the
documentation section "Creating custom models":

https://djangocms-custom-content.readthedocs.io/

Contrib examples
================

This package ships optional, small example apps under ``djangocms_custom_content.contrib``.
They are intended as quick starting points (models + admin + django CMS plugins) and can be
enabled in a project as-is or copied and adapted.

Available example modules:

* ``djangocms_custom_content.contrib.people``: Simple ``Person`` model + "Person" teaser plugin
* ``djangocms_custom_content.contrib.services``: Simple ``Service`` model + teaser + "featured services" plugin
* ``djangocms_custom_content.contrib.categories``: Simple taxonomy + category list plugin
* ``djangocms_custom_content.contrib.blog``: Simple blog posts with category relationship + teaser + latest posts plugin

To enable one (or more) of them, add the module(s) to ``INSTALLED_APPS`` and run migrations::

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


.. |PyPiVersion| image:: https://img.shields.io/pypi/v/djangocms-custom-content.svg?style=flat-square
    :target: https://pypi.python.org/pypi/djangocms-custom-content
    :alt: Latest PyPI version

.. |PyVersion| image:: https://img.shields.io/pypi/pyversions/djangocms-custom-content.svg?style=flat-square
    :target: https://pypi.python.org/pypi/djangocms-custom-content
    :alt: Python versions

.. |DjVersion| image:: https://img.shields.io/pypi/frameworkversions/django/djangocms-custom-content.svg?style=flat-square
    :target: https://pypi.python.org/pypi/djangocms-custom-content
    :alt: Django versions

.. |CmsVersion| image:: https://img.shields.io/pypi/frameworkversions/django-cms/djangocms-custom-content.svg?style=flat-square
    :target: https://pypi.python.org/pypi/djangocms-custom-content
    :alt: django CMS versions

.. |Coverage| image:: https://codecov.io/gh/fsbraun/djangocms-custom-content/graph/badge.svg?token=GESjKzHSXl
    :target: https://codecov.io/gh/fsbraun/djangocms-custom-content
