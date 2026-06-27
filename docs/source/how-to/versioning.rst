Implement Content Versioning
============================

djangocms-custom-content integrates with `djangocms-versioning
<https://github.com/django-cms/djangocms-versioning>`_ so each content object can
carry a full draft/published version history. The grouper provides the stable
identity; versioning manages the content rows underneath it.

Prerequisites
-------------

- ``djangocms-versioning`` installed and added to ``INSTALLED_APPS``.

``djangocms-custom-content`` registers itself as versioning-enabled
(``djangocms_versioning_enabled = True``); no further wiring is needed beyond
opting in per content model.

Activating versioning support
-----------------------------

Set ``enable_versioning = True`` in the content model's ``CMSConfig``:

.. code-block:: python

    class ArticleContent(AbstractCustomContent):
        article = models.ForeignKey(Article, on_delete=models.CASCADE)
        title = models.CharField(max_length=200)
        body = models.TextField()

        class CMSConfig:
            enable_versioning = True

The framework auto-detects the foreign key from the content model to its grouper
(``article`` above) and uses it as the versioning grouper field. You do not have
to name it explicitly.

Language-Based Versioning
-------------------------

If the content model declares a ``language`` field, it is automatically added as
an extra grouping field. Versions are then tracked **per language**, and the
admin version list gains a language filter scoped to the current site:

.. code-block:: python

    class ArticleContent(AbstractCustomContent):
        article = models.ForeignKey(Article, on_delete=models.CASCADE)
        language = models.CharField(max_length=8)
        title = models.CharField(max_length=200)
        body = models.TextField()

        class CMSConfig:
            enable_versioning = True

Without a ``language`` field, the content model is still fully versioned — just
in a single dimension (one version chain per grouper). The bundled
``contrib.people`` app is an example of a versioned model with no ``language``
field, while ``contrib.blog`` is an example of a per-language versioned model.

Accessing content
------------------

Use the grouper accessors to retrieve the current content for a language:

.. code-block:: python

    article = Article.objects.first()
    article.get_content(language="en")        # current published content
    article.get_admin_content(language="en")  # latest content (for admin)

See Also
--------

- :doc:`../explanation/architecture` - The grouper/content pattern
- :doc:`../tutorials/basic_setup` - Create a versioned content model
