Reference
==========

API reference automatically generated from source code.

``CMSConfig`` options
---------------------

Declare a ``CMSConfig`` inner class on a **content** model to opt into CMS
integration. All options are read at app startup and default to off.

.. list-table::
   :widths: 28 12 60
   :header-rows: 1

   * - Option
     - Default
     - Effect
   * - ``enable_versioning``
     - ``False``
     - Register the content model with djangocms-versioning (which must be
       installed). If the model has a ``language`` field, ``language`` is added
       as an extra grouping field, giving per-language version history.
   * - ``enable_frontend_editing``
     - ``False``
     - Make the content frontend-editable (double-click editing via the CMS
       toolbar). The grouper admin should mix in ``FrontendEditableAdminMixin``.
   * - ``apphook``
     - ``False``
     - Register a CMS app hook exposing a detail view. The URL uses the model's
       ``slug`` field if present, otherwise its ``pk``; a ``get_absolute_url()``
       is injected onto the model. Accepts an
       :class:`~djangocms_custom_content.apphooks.AppHookConfig` instead of
       ``True`` to supply views, extra URLs or a namespace field. No list view is
       generated — write a list plugin for the root page instead, see
       :ref:`apphook-root-page`. See :doc:`../how-to/apphooks`.
   * - ``admin_menu``
     - ``False``
     - Add a shortcut to the grouper changelist in the toolbar's admin (site)
       menu. Entries are sorted alphabetically above the *Administration*
       break and are only shown to users with view permission on the grouper.

Whether a content model participates as a grouper/content pair is inferred from
its foreign key to an :class:`~djangocms_custom_content.models.AbstractCustomGrouper`;
a content model without such a foreign key is treated as a plain model (no
versioning, apphook or grouper admin).

Related setting:

- ``CMS_SETTINGS_SHORTCUT`` (default ``True``) — show the settings-cog button for
  the current grouper in the toolbar.

.. _special-fields:

Special field names
-------------------

Two field names on a **content** model are read by the framework and change its
behaviour. Both are optional; name a field one of these only when you mean it.

``slug``
~~~~~~~~

Present, and the generated app hook routes on it —
``<slug:slug>/`` instead of ``<int:pk>/`` — and the injected
``get_absolute_url()`` builds the URL from it. Absent, and the detail URL uses
the primary key.

Because a detail URL has to identify a single object, a slug may be repeated only
*within* one grouper — across its versions and, if the model also has a
``language`` field, across its translations:

.. code-block:: python

    slug = models.SlugField(_("Slug"))    # not unique=True

.. warning::

   Do **not** declare ``unique=True`` on a versioned content model. Every version
   is a row of its own and they all carry the same slug, so a database-level
   unique constraint makes it impossible to create a second version.

Uniqueness *across* objects is validated instead of constrained.
:meth:`~djangocms_custom_content.models.AbstractCustomContent.validate_unique`
rejects a slug another object already uses — counting **every** version, not just
the current one, so a slug held by an archived version stays reserved and
reverting that version can never introduce an ambiguous URL. The grouper admin
repeats the check on its own form, where it can attach the error to the field the
editor typed in.

Should a duplicate reach the database anyway (an import, a data migration, a
``QuerySet.update()``), the detail view does not raise: it serves the first match
and logs an error naming the model, the slug and the pk it chose.

``language``
~~~~~~~~~~~~

Present on a content model that has a grouper, and the content is treated as
translatable:

- ``language`` becomes an extra grouping field, so version history is kept
  **per language** rather than per object;
- the grouper admin grows language tabs and a language column;
- the detail view filters by the active language, so a slug shared by an
  object's own translations resolves to the right one.

Add it as a plain character field — the framework reads the field, not a
particular type:

.. code-block:: python

    language = models.CharField(_("Language"), max_length=8)

Without this field a grouper has exactly one content object per version, which is
the simpler shape; ``contrib.people`` and ``contrib.services`` are built that way,
``contrib.blog`` has the field.

Models
------

.. autoclass:: djangocms_custom_content.models.AbstractCustomGrouper
   :members:
   :show-inheritance:

.. autoclass:: djangocms_custom_content.models.AbstractCustomContent
   :members:
   :show-inheritance:

.. autoclass:: djangocms_custom_content.models.CustomGrouperMixin
   :members:

.. autoclass:: djangocms_custom_content.models.CustomContentMixin
   :members:

Relations
---------

.. autoclass:: djangocms_custom_content.relations.RelationField
   :members:

.. autoclass:: djangocms_custom_content.relations.RelationManager
   :members:

.. autoclass:: djangocms_custom_content.relations.ReverseRelationManager
   :members:

.. autofunction:: djangocms_custom_content.relations.relation_through_factory

.. autofunction:: djangocms_custom_content.relations.grouper_model_of

CMS Toolbars
------------

.. autoclass:: djangocms_custom_content.cms_toolbars.CustomContentToolbar
   :members:
   :show-inheritance:

Admin
-----

.. autoclass:: djangocms_custom_content.admin.CustomGrouperAdminMixin
   :members:
   :show-inheritance:

.. autoclass:: djangocms_custom_content.relation_admin.RelationAdminMixin
   :members:
   :show-inheritance:

App hooks
---------

.. autoclass:: djangocms_custom_content.apphooks.AppHookConfig
   :members:

Helpers
-------

.. autofunction:: djangocms_custom_content.helpers.get_custom_config

.. toctree::
   :maxdepth: 1

   api_stability
