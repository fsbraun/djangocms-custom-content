Register the grouper admin
==========================

Content is edited **through the grouper admin**, not through a separate admin for
the content model. Registering the grouper with django CMS's
``GrouperModelAdmin`` plus
:class:`~djangocms_custom_content.admin.CustomGrouperAdminMixin` is what wires up
versioning, frontend editing, the toolbar entries, and the relation autocomplete
widgets. A plain ``admin.ModelAdmin`` gives you none of that.

The pattern
-----------

.. code-block:: python

    from cms.admin.placeholderadmin import FrontendEditableAdminMixin
    from cms.admin.utils import GrouperModelAdmin
    from django.contrib import admin

    from djangocms_custom_content.admin import CustomGrouperAdminMixin
    from .models import Article

    @admin.register(Article)
    class ArticleAdmin(CustomGrouperAdminMixin, FrontendEditableAdminMixin, GrouperModelAdmin):
        grouper_field_name = "article"   # the FK on ArticleContent pointing at Article

        list_display = ("content__title", "content__slug")
        search_fields = ("content__title", "content__body")
        prepopulated_fields = {"content__slug": ("content__title",)}

Key points:

- **Register only the grouper.** You do not register the content model yourself —
  versioning and the admin handle the content edit views for you.
- **Reach content fields with the** ``content__`` **prefix** in ``list_display``,
  ``search_fields``, ``prepopulated_fields`` and ``fieldsets``. The current
  language/version content is resolved behind that prefix.
- **Tell the admin where the content is** with either ``grouper_field_name``
  (the name of the foreign key on the content model, as above) or
  ``content_model = ArticleContent``.
- Add ``FrontendEditableAdminMixin`` only if the content model enables
  ``enable_frontend_editing``.
- If the content model has a ``language`` field, the language grouping column is
  added to the admin automatically — you do not set ``extra_grouping_fields``.

Relation fields in the admin
----------------------------

Any :class:`~djangocms_custom_content.relations.RelationField` on the grouper is
rendered automatically as an **autocomplete multi-select**, drag-sortable when
the relation is declared ``ordered=True`` (see
:class:`~djangocms_custom_content.relation_admin.RelationAdminMixin`, which
``CustomGrouperAdminMixin`` already includes). Two things are required for it to
work:

- The **target model must have a registered admin** that defines
  ``search_fields`` — the autocomplete searches the target through those fields
  (``content__`` prefixes are routed to the target's content model).
- The owning grouper admin must be a ``GrouperModelAdmin`` (so the autocomplete
  endpoint is served).

Opt out per admin with ``relation_autocomplete = False``.

Plain models
------------

A content model that has **no grouper** (for example a simple taxonomy like
``FlatCategory``) is just an ordinary model — register it with a normal
``admin.ModelAdmin``. The grouper admin pattern only applies to grouper/content
pairs.

See Also
--------

- :doc:`../explanation/architecture` - The grouper/content pattern
- :doc:`m2m_relations` - Declaring the relations that render as autocomplete
- :doc:`../reference/index` - ``CMSConfig`` options
