Article with CMS Plugins Tutorial
==================================

Build on the basic article model by adding CMS plugins and an app hook for frontend display.

This tutorial builds on the :doc:`basic_setup` tutorial.

Overview
--------

We'll extend the article model created earlier by:

- Creating CMS plugins to display articles
- Adding an app hook for article URLs
- Creating templates to render articles on the frontend

Step 1: Create CMS Plugins
---------------------------

Add ``my_content/cms_plugins.py``:

.. code-block:: python

    from cms.plugin_base import CMSPluginBase
    from cms.plugin_pool import plugin_pool
    from django.utils.translation import gettext_lazy as _
    from django.utils.translation import get_language
    from .models import ArticleContent

    @plugin_pool.register_plugin
    class ArticleTeaserPlugin(CMSPluginBase):
        name = _("Article Teaser")
        render_template = "my_content/article_teaser.html"

        def render(self, context, instance, placeholder):
            articles = ArticleContent.objects.filter(
                language=get_language()
            )[:3]
            return {
                **context,
                "articles": articles,
            }

    @plugin_pool.register_plugin
    class ArticleListPlugin(CMSPluginBase):
        name = _("Article List")
        render_template = "my_content/article_list.html"

        def render(self, context, instance, placeholder):
            articles = ArticleContent.objects.filter(
                language=get_language()
            ).order_by("-id")
            return {
                **context,
                "articles": articles,
            }

Step 2: Create Templates
------------------------

Create the template directory:

.. code-block:: bash

    mkdir -p my_content/templates/my_content

Create ``my_content/templates/my_content/article_teaser.html``:

.. code-block:: django

    <section class="article-teaser">
        <h2>Latest Articles</h2>
        <div class="articles-grid">
            {% for article in articles %}
                <article class="article-card">
                    <h3><a href="{% url 'article-detail' article.slug %}">{{ article.title }}</a></h3>
                    <p>{{ article.body|truncatewords:30 }}</p>
                    <a href="{% url 'article-detail' article.slug %}" class="btn">Read more</a>
                </article>
            {% empty %}
                <p>No articles yet.</p>
            {% endfor %}
        </div>
    </section>

Create ``my_content/templates/my_content/article_list.html``:

.. code-block:: django

    <section class="article-list">
        <h2>All Articles</h2>
        <ul class="articles">
            {% for article in articles %}
                <li>
                    <a href="{% url 'article-detail' article.slug %}">{{ article.title }}</a>
                </li>
            {% empty %}
                <p>No articles available.</p>
            {% endfor %}
        </ul>
    </section>

Create the article detail template ``my_content/templates/my_content/article_detail.html``:

.. code-block:: django

    {% extends "base.html" %}
    {% load cms_tags %}

    {% block content %}
        {% cms_edit_on %}
        <article class="article">
            <h1>{{ article.title }}</h1>
            <p class="meta">Published on {{ article.id }}</p>
            <div class="content">
                {{ article.body|safe }}
            </div>
        </article>
        {% cms_edit_off %}
    {% endblock %}

Step 3: Enable App Hook
-----------------------

To enable URL routing for articles, add ``apphook = True`` to ``ArticleContent.CMSConfig``:

Update ``my_content/models.py``:

.. code-block:: python

    class ArticleContent(AbstractCustomContent):
        """The editable article content."""
        article = models.ForeignKey(Article, on_delete=models.CASCADE)
        title = models.CharField(max_length=200)
        slug = models.SlugField()
        body = models.TextField()

        class CMSConfig:
            # Make editable in frontend and versionable
            editable = True
            versionable = True
            # Enable URL routing via app hook
            apphook = True

        def __str__(self):
            return self.title

That's all you need! The generic detail view will automatically handle URL routing.

Step 4: Add the App Hook to a CMS Page
---------------------------------------

In the Django CMS admin:

1. Create a new Django CMS page (or edit an existing one)
2. Go to the **Advanced** tab
3. Under **Application**, select your app hook ("My Content")
4. Save the page

The generic detail view automatically handles displaying articles by slug.

Done!
-----

Your article model now has:

✅ CMS plugins for teaser and list display
✅ An app hook for frontend URLs
✅ Proper templates
✅ Frontend display of articles

Next Steps:

- :doc:`model_with_m2m` - Add authors to articles using M2M relations
- :doc:`../how-to/m2m_relations` - Learn more about generic M2M relations
- :doc:`../explanation/architecture` - Understand the grouper/content pattern
