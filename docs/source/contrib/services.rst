Services Module
===============

Service/product showcase with descriptions and features.

Installation
-----------

.. code-block:: python

    INSTALLED_APPS = [
        "djangocms_custom_content",
        "djangocms_custom_content.contrib.services",
    ]

.. code-block:: bash

    python manage.py migrate

Models
------

**Service** - Groups all language versions of a service
**ServiceContent** - Language-specific service information

Fields: ``title``, ``slug``, ``description``, ``icon``

Usage
-----

.. code-block:: python

    from djangocms_custom_content.contrib.services.models import Service, ServiceContent

    service = Service.objects.create()
    ServiceContent.objects.create(
        service=service,
        language="en",
        title="Web Development",
        slug="web-development",
        description="Professional web development services...",
    )

Plugins
-------

- ``ServiceTeaser`` - Display a single service
- ``ServiceList`` - Display all services

Admin
-----

Registered with standard display and search.

See Also
--------

- :doc:`../reference/index` - API reference
