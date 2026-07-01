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
       is injected onto the model. See :doc:`../how-to/apphooks`.
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

Helpers
-------

.. autofunction:: djangocms_custom_content.helpers.get_custom_config
