========================
djangocms-custom-content
========================

Custom content plugin for django CMS providing flexible template-based content blocks.

Description
===========

``djangocms-custom-content`` is a versatile plugin for django CMS that allows content
editors to create flexible, template-based content blocks. It provides a simple way
to add custom content areas to your django CMS pages.

Features
========

* Flexible template-based content rendering
* Compatible with django CMS 3.11, 4.1, and 5.0
* Support for Django 4.2 through 6.0
* Easy integration with existing django CMS projects
* Support for child plugins

Installation
============

Install the package using pip::

    pip install djangocms-custom-content

Add it to your ``INSTALLED_APPS``::

    INSTALLED_APPS = [
        ...
        'djangocms_custom_content',
        ...
    ]

Run migrations::

    python manage.py migrate djangocms_custom_content

Usage
=====

After installation, you'll find a "Custom Content" plugin in the django CMS
plugin menu. Add it to any placeholder and configure the template and content
as needed.

Contributing
============

Contributions are welcome! Please feel free to submit a Pull Request.

License
=======

This project is licensed under the BSD-3-Clause License.
