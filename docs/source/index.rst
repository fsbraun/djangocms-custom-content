.. djangocms-custom-content documentation master file

djangocms-custom-content
========================

Developer framework for integrating custom content models with django CMS.

``djangocms-custom-content`` provides a fast, flexible way to build custom content types
and integrate them with django CMS. It handles the common integration pieces (versioning,
frontend-editing, relationships) so you can focus on your content models, and their admin handling.

----

🧭 Choose your path
-------------------

.. grid:: 2
   :gutter: 3

   .. grid-item-card:: 🚀 Tutorials
      :link: tutorials/index
      :link-type: doc

      Step-by-step lessons to get you started. Install the package,
      create your first content model, and build a complete blog system.

   .. grid-item-card:: 🛠 How-to guides
      :link: how-to/index
      :link-type: doc

      Practical, goal-oriented guides for solving specific problems:
      M2M relations, versioning, admin customization.

   .. grid-item-card:: 🧠 Explanation
      :link: explanation/index
      :link-type: doc

      Understand the concepts and design patterns behind the framework:
      the grouper/content architecture and generic M2M relations.

   .. grid-item-card:: 📖 Reference
      :link: reference/index
      :link-type: doc

      Authoritative API reference auto-generated from source code.
      Classes, managers, functions, and configuration options.

----

✨ Key Features
---------------

* **Fast setup** — Define models and get instant CMS integration
* **Multi-language support** — Built-in language/versioning per content model
* **Generic M2M relations** — Connect to any Django model without hardcoding FKs
* **Ready-to-use examples** — Contrib modules for common patterns (blog, people, categories)
* **Clean architecture** — Simple grouper/content pattern avoiding boilerplate
* **Django CMS 5.0+** — Compatible with modern django CMS and Django versions


Contents
--------

.. toctree::
   :maxdepth: 2
   :hidden:

   tutorials/index
   how-to/index
   explanation/index
   reference/index

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
