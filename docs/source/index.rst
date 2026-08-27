.. djangocms-custom-content documentation master file

djangocms-custom-content
========================

**Custom content types for django CMS — without the boilerplate.**

Building a custom content type in django CMS by hand means wiring up a grouper,
versioning, a grouper admin, frontend editing, an app hook and migrations
yourself. ``djangocms-custom-content`` does all of that — you write the model.

----

✍️ Write this…
--------------

.. code-block:: python

    from django.db import models
    from djangocms_custom_content.models import AbstractCustomGrouper, AbstractCustomContent

    class Article(AbstractCustomGrouper):
        pass

    class ArticleContent(AbstractCustomContent):
        article = models.ForeignKey(Article, on_delete=models.CASCADE)
        language = models.CharField(max_length=10)
        slug = models.SlugField()
        title = models.CharField(max_length=200)
        body = models.TextField()

        class CMSConfig:
            enable_versioning = True
            enable_frontend_editing = True
            apphook = True

…and that model (plus a few lines of grouper admin) gives you, for free:

* 📝 **per-language draft/publish version history**
* 🖱️ **frontend, double-click editing** inside the page
* 🔗 **a detail view at a clean URL**, with ``get_absolute_url()`` injected
* 🗂️ **a grouper admin** to create and manage content

Want related content? Add **one line** to the grouper —
``authors = RelationField("people.Person", ordered=True)`` — and the admin renders
a **sortable autocomplete**, anchored to the grouper so the link survives every
new version.

.. note::

   **Status: 0.5 — usable, pre-1.0.** The relations system is a ground-up rewrite
   and the framework runs the bundled apps and test suite, but APIs may still
   shift before 1.0. Feedback and bug reports are very welcome.

----

🚀 See it work in two minutes
-----------------------------

Don't build anything yet — turn on a bundled example and click around first.

.. code-block:: bash

    pip install djangocms-custom-content

Add the blog (plus the apps it relates to) to ``INSTALLED_APPS`` and migrate:

.. code-block:: python

    INSTALLED_APPS = [
        # ... django CMS and its dependencies ...
        "djangocms_custom_content",
        "djangocms_custom_content.contrib.people",
        "djangocms_custom_content.contrib.categories",
        "djangocms_custom_content.contrib.blog",
    ]

.. code-block:: bash

    python manage.py migrate

That's it. You now have a **versioned, frontend-editable blog** in the admin,
with **sortable authors** and **categories** relations and ready-to-place CMS
plugins — no models written. Poke at it, then build your own.

**Ready to build your own? →** :doc:`Create your first model in 5 minutes <tutorials/basic_setup>`

.. tip::

   No django CMS project yet? Follow the
   `django CMS installation guide <https://docs.django-cms.org/en/latest/introduction/01-install.html>`_
   first, then come back. Curious how a bundled piece works? Each app has a short
   tour: :doc:`blog <how-to/blog>`, :doc:`people <how-to/people>`,
   :doc:`categories <how-to/categories>`, :doc:`services <how-to/services>`.

----

🧭 Choose your path
-------------------

.. grid:: 2
   :gutter: 3

   .. grid-item-card:: 🚀 Tutorials
      :link: tutorials/index
      :link-type: doc

      Step-by-step lessons. Install the package, create your first content
      model, then add plugins, an app hook and relations.

   .. grid-item-card:: 🛠 How-to guides
      :link: how-to/index
      :link-type: doc

      Goal-oriented guides: register the grouper admin, expose content at a URL,
      declare relations, and enable versioning.

   .. grid-item-card:: 🧠 Explanation
      :link: explanation/index
      :link-type: doc

      The concepts behind the framework: the grouper/content pattern and how
      grouper-anchored relations work.

   .. grid-item-card:: 📖 Reference
      :link: reference/index
      :link-type: doc

      Authoritative API reference: classes, managers, functions, and the
      ``CMSConfig`` options.

----

✨ Key Features
---------------

* **Write the model, skip the plumbing** — versioning, grouper admin, frontend
  editing, app hooks and migrations are handled (:doc:`tutorials/basic_setup`)
* **Relations that survive versioning** — related content is anchored to the
  grouper, so links don't break when a new version is published
  (:doc:`explanation/relationships`)
* **Sortable related-content widgets, free** — every relation renders as an
  autocomplete multi-select in the admin, drag-sortable when ordered
  (:doc:`how-to/admin`)
* **Relate to anything without touching it** — generic relations need no foreign
  key or migration on the target model (:doc:`how-to/m2m_relations`)
* **Multi-language & versioned** — per-language draft/publish history per content
  model (:doc:`how-to/versioning`)
* **Batteries included** — bundled blog, people, categories and services apps to
  use as-is or copy and adapt (:doc:`how-to/blog`)
* **Current django CMS** — see the badges on `PyPI
  <https://pypi.python.org/pypi/djangocms-custom-content>`_ for the supported
  django CMS, Django and Python releases


Contents
--------

.. toctree::
   :maxdepth: 2
   :hidden:

   tutorials/index
   how-to/index
   explanation/index
   reference/index
   changelog
