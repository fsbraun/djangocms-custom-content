.. djangocms-custom-content documentation master file

Welcome to djangocms-custom-content's documentation!
====================================================

``djangocms-custom-content`` is a custom content plugin for django CMS
that provides flexible template-based content blocks.

Features
--------

* Flexible template-based content rendering
* Compatible with django CMS 3.11, 4.1, and 5.0
* Support for Django 4.2 through 6.0
* Easy integration with existing django CMS projects

Contents
--------

.. toctree::
   :maxdepth: 2

   installation
   usage
   reference

Installation
============

Install the package using pip:

.. code-block:: bash

    pip install djangocms-custom-content

Add it to your ``INSTALLED_APPS``:

.. code-block:: python

    INSTALLED_APPS = [
        ...
        'djangocms_custom_content',
        ...
    ]

Run migrations:

.. code-block:: bash

    python manage.py migrate djangocms_custom_content


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
