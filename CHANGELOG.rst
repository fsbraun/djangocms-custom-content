=========
Changelog
=========

All notable changes to this project are documented here. Versions follow
`Semantic Versioning <https://semver.org/>`_; while the package is at ``0.x`` a
minor bump may still carry breaking changes.


0.6.0 (2026-08-26)
==================

Breaking changes
----------------

* **Contrib templates moved into their apps.** Every bundled template now lives
  in the app that uses it, in a directory named after that app's label. The old
  central ``djangocms_custom_content/templates/djangocms_custom_content/contrib/``
  tree is gone. Projects that override a bundled template must move the override
  to the new path:

  .. list-table::
     :header-rows: 1

     * - Old path
       - New path
     * - ``djangocms_custom_content/contrib/blog/blog_post_teaser.html``
       - ``djangocms_custom_content_blog/blog_post_teaser.html``
     * - ``blog/detail.html``
       - ``djangocms_custom_content_blog/blogpostcontent_detail.html``
     * - ``djangocms_custom_content/contrib/categories/category_list.html``
       - ``djangocms_custom_content_categories/category_list.html``
     * - ``djangocms_custom_content/contrib/services/service_teaser.html``
       - ``djangocms_custom_content_services/service_teaser.html``
     * - ``djangocms_custom_content/contrib/services/featured_services.html``
       - ``djangocms_custom_content_services/featured_services.html``

  The blog detail template used the generic ``blog/`` namespace, which collided
  with any project that has its own ``blog`` app. Prefixing every path with the
  app label removes that whole class of clash.

* **``contrib.services`` is now a grouper/content pair.** ``Service`` was a plain
  model holding its own fields; it is now an ``AbstractCustomGrouper`` with the
  fields moved to a new versioned ``ServiceContent``. Code reading
  ``service.title`` must go through ``service.get_content().title``, and
  ``ServiceContent.slug`` is no longer unique (versions of one service share a
  slug). Shipped as a single squashed ``0001_initial``, so an existing
  installation of the previous schema has no upgrade path — this example app had
  no releases in the wild.

* ``BlogPostContent.get_template()`` was removed. The renamed detail template now
  matches the default ``{app_label}/{model_name}_detail.html`` convention, which
  all four contrib apps follow.

* Removed three templates that nothing referenced:
  ``djangocms_custom_content/default.html``,
  ``djangocms_custom_content/contrib/blog/latest_blog_posts.html`` and
  ``djangocms_custom_content/contrib/people/person_teaser.html`` (superseded by
  the app-local ``djangocms_custom_content_people/person_teaser.html``).

* The ``verbose_name`` of two contrib app configs changed: "Custom Content -
  Categories (Example)" is now "Global categories", and "Custom Content -
  Services (Example)" is now "Services".

Added
-----

* **``CMSConfig.apphook`` accepts an**
  :class:`~djangocms_custom_content.apphooks.AppHookConfig`, supplying a detail
  view, extra URL patterns, the routing field, an application namespace and an
  optional list view. ``apphook = True`` is unchanged shorthand for the defaults,
  so existing app hooks keep working.
* **No list view is generated for an app hook root, by design.** The root is an
  ordinary CMS page, so the index belongs to a list plugin an editor can arrange
  alongside anything else on that page. The framework ships no such plugin — it
  would need a concrete model and a migration, and what to list is an application
  decision — but ``contrib.blog`` now carries a complete worked example,
  ``BlogPostListPlugin``, including pagination. See :ref:`apphook-root-page`.
* **More than one app hook page.** ``AppHookConfig(namespace_field=...)`` names a
  field on the grouper holding the app hook instance an object belongs to, so
  ``get_absolute_url()`` reverses with ``current_app`` and links stay on the page
  the visitor is on. Unset, behaviour is unchanged.
* ``admin_menu = True`` on a content model's ``CMSConfig`` adds a shortcut to its
  changelist in the toolbar's admin menu. Grouper-backed content links to the
  grouper changelist; plain content such as ``FlatCategory`` links to its own.
* Toolbar shortcuts can be switched off with ``CMS_SETTINGS_SHORTCUT = False``.
* ``contrib.services`` opts into ``enable_versioning`` and
  ``enable_frontend_editing``, making it the example of a grouper/content pair
  without a ``language`` field.
* django CMS 5.1 added to the CI matrix, alongside 5.0 and main.
* Documentation: how to render a reverse relation in a detail view (listing the
  blog posts a person authored), and how to override a bundled template.

Fixed
-----

* **A slugless app hook crashed at startup.** ``register_apphook`` tested for a
  slug field with ``_meta.get_field("slug") is not None``, which raises rather
  than returning ``None``, so the primary-key routing branch was unreachable. A
  content model with ``apphook = True`` and no ``slug`` now routes on ``<int:pk>/``
  as documented.
* **A translated object broke its own detail view.** The generated app hook's
  detail view never narrowed by language, so a content model with a ``language``
  field matched its own translations and raised ``MultipleObjectsReturned``. The
  view now filters by the active language.
* **Duplicate slugs across objects returned a server error**
  (`#20 <https://github.com/fsbraun/djangocms-custom-content/issues/20>`_). A
  slug now has to identify a single object:
  :meth:`~djangocms_custom_content.models.AbstractCustomContent.validate_unique`
  and the grouper admin form reject a slug another object already uses, counting
  every version rather than only the current one. A slug may still be repeated
  within one object, across its versions and translations. Should a duplicate
  reach the database regardless, the detail view serves the first match and logs
  an error instead of raising. See :ref:`special-fields`.
* **Groupers returned the wrong content.** ``AbstractCustomGrouper`` cached the
  related manager on the *class*, so every grouper of a model reported the
  content of the first one instantiated in the process — visible as wrong labels
  in relation widgets and admin columns. Only the accessor *name* is cached now;
  the manager is resolved per instance.
* The toolbar's "settings" link and gear now carry the content object being
  viewed, so a published version and its newer draft no longer open the same
  form. Requires django CMS 5.1 or later; on 5.0 the link falls back to editing
  the latest content, as before.
* ``BlogPostTeaserPlugin`` passed the grouper to a template expecting content, so
  teasers rendered empty. ``PersonTeaserPlugin`` set a context key the template
  did not read.
* The blog detail template referenced ``instance`` (the context variable is the
  model name) and ``publish_date`` (the field is ``published_at``); the person
  detail template referenced a ``bio`` field that does not exist. All three
  rendered blank.
* Ordered relations no longer lose their order when read back through an
  unordered code path.
* ``contrib.services`` plugin models were missing ``related_name`` on
  ``cmsplugin_ptr``, leaving ``makemigrations --check`` permanently dirty.

Performance
-----------

* Relation writes persist only the delta rather than rewriting the whole edge
  set, and the relation admin issues fewer queries.

Packaging
---------

* ``package-data`` now applies ``templates/**/*`` to every package rather than
  only the top-level one, so each contrib app ships its own templates.


0.5.0 (2026-06-27)
==================

First published release. Earlier history is in the
`commit log <https://github.com/fsbraun/djangocms-custom-content/commits/main>`_.
