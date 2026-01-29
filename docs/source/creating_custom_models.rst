Creating custom models
======================

This package is designed to be extended in your project: you create your own Django
models and wire them into django CMS via plugins.

A minimal workflow
------------------

1. Create a Django app in your project (e.g. ``my_content``).
2. Add your app to ``INSTALLED_APPS``.
3. Define your content model(s).
4. Provide one or more django CMS plugins that render your content.
5. Add templates for your plugins.
6. Run ``python manage.py makemigrations`` and ``python manage.py migrate``.

Example: a model + teaser plugin
--------------------------------

Model:

.. code-block:: python

    # my_content/models.py
    from cms.models import CMSPlugin
    from django.db import models


    class Article(models.Model):
        title = models.CharField(max_length=200)
        slug = models.SlugField(unique=True)
        teaser = models.TextField(blank=True)

        def __str__(self):
            return self.title


    class ArticleTeaser(CMSPlugin):
        article = models.ForeignKey(Article, on_delete=models.PROTECT)


Plugin:

.. code-block:: python

    # my_content/cms_plugins.py
    from cms.plugin_base import CMSPluginBase
    from cms.plugin_pool import plugin_pool

    from .models import ArticleTeaser


    @plugin_pool.register_plugin
    class ArticleTeaserPlugin(CMSPluginBase):
        model = ArticleTeaser
        name = "Article"
        render_template = "my_content/article_teaser.html"
        cache = True


Template:

.. code-block:: django

    {# templates/my_content/article_teaser.html #}
    <article>
      <h3>{{ instance.article.title }}</h3>
      {% if instance.article.teaser %}<p>{{ instance.article.teaser }}</p>{% endif %}
    </article>

Tips
----

- If you want a realistic starting point with working models + admin + CMS plugins,
  check the shipped example apps under ``djangocms_custom_content.contrib``.
- For richer architectures, add relationships (FK/M2M) between your models and expose
  them via dedicated plugins (e.g. "related" or "featured" queries).
