Contrib examples
================

``djangocms-custom-content`` ships optional example apps under
``djangocms_custom_content.contrib``. They are intended as small, readable starting
points that demonstrate typical patterns:

- model-based content
- Django admin registration
- django CMS plugins for rendering
- simple "featured" / list-style plugins

Available modules
-----------------

- ``djangocms_custom_content.contrib.people``
- ``djangocms_custom_content.contrib.services``
- ``djangocms_custom_content.contrib.categories``
- ``djangocms_custom_content.contrib.blog``

Enabling them
-------------

Add one or more modules to ``INSTALLED_APPS`` and run migrations.

.. code-block:: python

    INSTALLED_APPS = [
        ...,
        "djangocms_custom_content",
        "djangocms_custom_content.contrib.people",
        "djangocms_custom_content.contrib.services",
        "djangocms_custom_content.contrib.categories",
        "djangocms_custom_content.contrib.blog",
        ...,
    ]

.. code-block:: bash

    python manage.py migrate
