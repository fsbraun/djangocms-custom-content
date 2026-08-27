API stability
=============

What this package promises not to break, how long a deprecation lasts, and which
versions of django CMS, Django and Python it is supported on.

.. note::

   The package is at ``0.x``. Until 1.0 these rules describe *intent* rather than
   a guarantee — a minor release may still contain a breaking change, and the
   changelog says so when it does.

The public API
--------------

Anything listed here is covered by the deprecation policy below. Everything else
— including any name starting with an underscore — is internal and may change in
any release.

**Model bases**

- :class:`djangocms_custom_content.models.AbstractCustomGrouper`, and its
  ``get_content()`` / ``get_admin_content()`` methods
- :class:`djangocms_custom_content.models.AbstractCustomContent`, and its
  ``get_template()``, ``validate_unique()`` and ``find_slug_conflicts()`` methods
  along with the ``objects`` and ``admin_manager`` managers

**Relations**

- :class:`djangocms_custom_content.relations.RelationField` and its arguments
  (``target``, ``related_name``, ``ordered``, ``through_name``)
- the accessor API returned by a relation: ``all()``, ``filter()``, ``count()``,
  ``exists()``, ``add()``, ``remove()``, ``set()``, ``clear()`` and — for ordered
  relations — ``reorder()``
- :func:`djangocms_custom_content.relations.iter_relation_fields`

**Admin and forms**

- :class:`djangocms_custom_content.admin.CustomGrouperAdminMixin`
- :class:`djangocms_custom_content.forms.RelationModelForm`

**App hooks**

- :class:`djangocms_custom_content.apphooks.AppHookConfig` and its arguments

**Declarations read by the framework**

- the ``CMSConfig`` inner class and its options (see :doc:`index`)
- the special field names ``slug`` and ``language`` (see :ref:`special-fields`)

**Templates**

- the bundled template paths, which are how you override the markup
  (see :ref:`overriding-a-bundled-template`)
- the ``{app_label}/{model_name}_detail.html`` naming convention and the context
  variable named after the model

**Settings**

- ``CMS_SETTINGS_SHORTCUT``

Explicitly *not* public
-----------------------

- ``djangocms_custom_content.cms_config`` — the app-registry wiring
- ``djangocms_custom_content.views`` — the generated detail view and its mixins
  are an implementation detail of the app hook; subclass at your own risk
- ``djangocms_custom_content.relation_admin`` — widget and autocomplete plumbing
- ``djangocms_custom_content.helpers``
- everything under ``djangocms_custom_content.contrib`` — see
  :ref:`contrib-stability`
- the shape of generated through models and app hook classes

Deprecation policy
------------------

From 1.0 onwards:

- A public name is never removed without first being deprecated.
- A deprecation is announced in the changelog, raises
  ``DeprecationWarning`` when used, and keeps working for **two minor releases**
  (deprecate in 1.2, remove no earlier than 1.4).
- Behaviour changes that cannot be expressed as a rename — a default flipping,
  say — get a release note in the changelog under **Breaking changes** and, where
  it is possible, a transitional setting.
- Security fixes and changes forced by an upstream django CMS release are exempt;
  those are called out in the changelog instead.

.. _contrib-stability:

The ``contrib`` apps
--------------------

``djangocms_custom_content.contrib.*`` ships **complete applications**, not
sketches. They double as worked examples of the framework, but they are meant to
be installed and relied on:

- their models, plugins, templates and admin classes are covered by the
  deprecation policy above;
- **migrations are a continuity promise.** Every schema change arrives as a
  migration that upgrades an existing installation, with its data. Migrations are
  not squashed in a way that strands a database;
- their template paths are public, so overrides keep working (see
  :ref:`overriding-a-bundled-template`).

Copying an app into your own project remains a perfectly good way to start from
one — the framework underneath is what makes that easy — but you do not have to.

.. note::

   The continuity promise starts at **0.9.0**. One earlier change does not honour
   it: ``contrib.services`` was reshaped from a plain model into a grouper/content
   pair and re-issued as a single ``0001_initial``, which a database that
   installed the 0.5.0 app silently skips. If that is you, copy the 0.5.0 services
   app into your own project rather than upgrading to this one — see the 0.9.0
   entry in :doc:`../changelog`. There are no other such breaks.

Supported versions
------------------

A release supports the combinations it is tested against in CI. Rather than
repeat them here, where they would drift out of date, the badges below read the
released package's own metadata:

|PyVersion| |DjVersion| |CmsVersion|

.. |PyVersion| image:: https://img.shields.io/pypi/pyversions/djangocms-custom-content?style=flat-square&label=Python
    :target: https://pypi.python.org/pypi/djangocms-custom-content
    :alt: Supported Python versions

.. |DjVersion| image:: https://img.shields.io/pypi/frameworkversions/django/djangocms-custom-content?style=flat-square&label=Django
    :target: https://pypi.python.org/pypi/djangocms-custom-content
    :alt: Supported Django versions

.. |CmsVersion| image:: https://img.shields.io/pypi/frameworkversions/django-cms/djangocms-custom-content?style=flat-square&label=django%20CMS
    :target: https://pypi.python.org/pypi/djangocms-custom-content
    :alt: Supported django CMS versions

``djangocms-versioning`` is an optional dependency — the versioning package
``enable_versioning`` integrates with. The extra is named after the package
rather than after the feature, since versioning is a concept and this is one
implementation of it:

.. code-block:: bash

    pip install djangocms-custom-content[djangocms-versioning]

Dropping a Python, Django or django CMS version is a **minor** release change and
is announced in the changelog. Adding support for a new one is not breaking and
may happen in any release.

.. note::

   On the oldest supported django CMS one feature degrades rather than failing.
   The toolbar's settings link cannot name the version being viewed, because
   ``GrouperModelAdmin.content_pk_url_param`` was added later; the link opens the
   **latest** content instead, which is what that release has always done.
   Everything else behaves identically, and the test suite runs against every
   supported release.
