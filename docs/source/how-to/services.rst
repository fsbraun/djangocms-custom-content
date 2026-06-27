Using the contrib.services module
=================================

Service/product showcase with descriptions and features.

Installation
------------

.. code-block:: python

    INSTALLED_APPS = [
        "djangocms_custom_content",
        "djangocms_custom_content.contrib.services",
    ]

.. code-block:: bash

    python manage.py migrate

Models
------

**Service** - A single, plain Django model (not a grouper/content pair and not
versioned). It is included as an example of a simple model that the plugins can
showcase.

Fields: ``title``, ``slug``, ``summary``, ``description``, ``is_featured``

Usage
-----

.. code-block:: python

    from djangocms_custom_content.contrib.services.models import Service

    Service.objects.create(
        title="Web Development",
        slug="web-development",
        summary="Short teaser text...",
        description="Professional web development services...",
        is_featured=True,
    )

Plugins
-------

- ``ServiceTeaserPlugin`` ("Service teaser", model ``ServiceTeaser``) - Display
  a single selected service
- ``FeaturedServicesPlugin`` ("Featured services", model ``FeaturedServices``) -
  Display featured services, limited by a configurable count

Admin
-----

Registered with standard display and search.

See Also
--------

- :doc:`../reference/index` - API reference
