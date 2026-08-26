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

**Service** - The grouper. It carries no fields of its own: it is the stable
identity that plugins point at, so publishing a new version never invalidates a
plugin's foreign key.

**ServiceContent** - The versioned content, one row per version.

Fields: ``title``, ``slug``, ``summary``, ``description``, ``is_featured``

``ServiceContent`` opts into versioning and frontend editing:

.. code-block:: python

    class CMSConfig:
        enable_versioning = True
        enable_frontend_editing = True
        admin_menu = True

There is no ``language`` field, so a service has one content object per version
rather than one per language. Add a ``language`` field (as
:doc:`blog` does) if you need translations.

Usage
-----

Create the grouper first, then its content. Use ``with_user()`` so
djangocms-versioning can record who created the version:

.. code-block:: python

    from djangocms_custom_content.contrib.services.models import Service, ServiceContent

    service = Service.objects.create()
    ServiceContent.objects.with_user(request.user).create(
        service=service,
        title="Web Development",
        slug="web-development",
        summary="Short teaser text...",
        description="Professional web development services...",
        is_featured=True,
    )

Reading content back goes through the grouper, which returns the content for the
current version:

.. code-block:: python

    service.get_content()          # published content (frontend)
    service.get_admin_content()    # latest content (admin)

The default manager only yields **published** content, so unpublished services
disappear from the frontend on their own:

.. code-block:: python

    ServiceContent.objects.filter(is_featured=True)        # published only
    ServiceContent.admin_manager.filter(is_featured=True)  # every version

Frontend editing
----------------

``enable_frontend_editing`` renders a service through
``djangocms_custom_content_services/servicecontent_detail.html`` -- the default
``{app_label}/{model_name}_detail.html`` convention. Override that template in
your project to change how a service looks. It carries a ``service_details``
placeholder, so editors can add plugins to a service.

Plugins
-------

- ``ServiceTeaserPlugin`` ("Service teaser", model ``ServiceTeaser``) - Display
  a single selected service. The plugin's foreign key points at the **grouper**;
  ``render()`` resolves it to the current content.
- ``FeaturedServicesPlugin`` ("Featured services", model ``FeaturedServices``) -
  Display featured services, limited by a configurable count

Admin
-----

Registered with ``CustomGrouperAdminMixin`` and ``GrouperModelAdmin``, so one
change form edits the grouper and its content together. Content fields are
addressed with the ``content__`` prefix (``content__title``,
``content__slug``, ...). A published version is shown read-only; create a new
draft to edit it.

What this app demonstrates
--------------------------

The **grouper/content pair without a language field** -- the simplest shape that
still gets versioning and frontend editing. Compare it with:

- :doc:`blog` - the same pattern *with* a language field and relations
- :doc:`categories` - content **without** a grouper, so no versioning

See Also
--------

- :doc:`admin` - When to use the grouper admin versus a plain admin
- :doc:`../reference/index` - API reference
