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

``djangocms_custom_content.contrib.*`` holds **example applications**. They exist
to be read and copied, not to be depended on:

- their models, migrations, templates and admin classes may change or be removed
  in any release;
- migrations may be squashed without an upgrade path;
- they are not covered by the deprecation policy.

If you want a blog, a people directory or a service list in production, copy the
app into your own project and own it there. What *is* covered is the framework the
examples are built on — the model bases, relations and ``CMSConfig`` options.

Supported versions
------------------

A release supports the combinations it is tested against in CI:

.. list-table::
   :header-rows: 1

   * - Dependency
     - Supported
   * - Python
     - 3.10 – 3.14
   * - Django
     - 5.2, 6.0, 6.1
   * - django CMS
     - 5.0, 5.1
   * - djangocms-versioning
     - 2.3+ (optional; required by ``enable_versioning``)

Install the versioning support with the extra:

.. code-block:: bash

    pip install djangocms-custom-content[versioning]

Dropping a Python, Django or django CMS version is a **minor** release change and
is announced in the changelog. Adding support for a new one is not breaking and
may happen in any release.

.. note::

   On django CMS 5.0 one feature degrades rather than failing: the toolbar's
   settings link cannot name the version being viewed, because
   ``GrouperModelAdmin.content_pk_url_param`` only exists from 5.1. The link
   opens the **latest** content instead, which is the behaviour 5.0 has always
   had. Everything else is supported identically, and the test suite runs against
   both.
