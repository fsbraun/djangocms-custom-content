Blog Example Tutorial
=====================

Learn by building a complete blog system with tags, categories, and featured posts.

This tutorial builds on the :doc:`basic_setup` tutorial.

Overview
--------

We'll create:

- ``BlogPost`` model (the grouper)
- ``BlogPostContent`` model (the content)
- A teaser plugin to show featured blog posts
- A list plugin to show all blog posts

Step 1: Create Blog Models
---------------------------

Create ``my_blog/models.py``:

.. code-block:: python

    from django.db import models
    from django.utils.translation import gettext_lazy as _
    from djangocms_custom_content.models import (
        AbstractCustomGrouper,
        AbstractCustomContent,
    )

    class BlogPost(AbstractCustomGrouper):
        """Groups blog post content by language/version."""
        slug = models.SlugField(unique=True)

        class Meta:
            verbose_name = _("Blog Post")

        def __str__(self):
            return self.slug

    class BlogPostContent(AbstractCustomContent):
        """The actual blog post content."""
        post = models.ForeignKey(BlogPost, on_delete=models.CASCADE)
        title = models.CharField(max_length=200)
        slug = models.SlugField()
        excerpt = models.TextField(blank=True)
        body = models.TextField()
        is_featured = models.BooleanField(default=False)
        published_at = models.DateTimeField(auto_now_add=True)
        language = models.CharField(max_length=5, default="en")

        class Meta:
            verbose_name = _("Blog Post Content")
            ordering = ("-published_at",)

        def __str__(self):
            return self.title

        def get_template(self):
            return "my_blog/post_detail.html"

Step 2: Create CMS Plugins
---------------------------

Create ``my_blog/cms_plugins.py``:

.. code-block:: python

    from cms.plugin_base import CMSPluginBase
    from cms.plugin_pool import plugin_pool
    from django.utils.translation import gettext_lazy as _
    from django.utils.translation import get_language
    from .models import BlogPostContent

    @plugin_pool.register_plugin
    class BlogTeaserPlugin(CMSPluginBase):
        name = _("Blog Post Teaser")
        render_template = "my_blog/teaser.html"

        def render(self, context, instance, placeholder):
            featured = BlogPostContent.objects.filter(
                is_featured=True,
                language=get_language()
            )[:3]
            return {
                **context,
                "featured_posts": featured,
            }

    @plugin_pool.register_plugin
    class BlogListPlugin(CMSPluginBase):
        name = _("Blog Post List")
        render_template = "my_blog/list.html"

        def render(self, context, instance, placeholder):
            posts = BlogPostContent.objects.filter(
                language=get_language()
            )
            return {
                **context,
                "posts": posts,
            }

Step 3: Create Templates
------------------------

Create template directory:

.. code-block:: bash

    mkdir -p my_blog/templates/my_blog

``my_blog/templates/my_blog/teaser.html``:

.. code-block:: django

    <section class="featured-posts">
        <h2>Featured Posts</h2>
        {% for post in featured_posts %}
            <article>
                <h3>{{ post.title }}</h3>
                <p>{{ post.excerpt }}</p>
                <a href="{% url 'blog-post-detail' post.slug %}">Read more</a>
            </article>
        {% endfor %}
    </section>

``my_blog/templates/my_blog/list.html``:

.. code-block:: django

    <section class="blog-posts">
        <h2>All Posts</h2>
        <div class="post-list">
            {% for post in posts %}
                <article class="post-summary">
                    <h3>{{ post.title }}</h3>
                    <time>{{ post.published_at|date:"Y-m-d" }}</time>
                    <p>{{ post.excerpt }}</p>
                    <a href="{% url 'blog-post-detail' post.slug %}">Read full post</a>
                </article>
            {% endfor %}
        </div>
    </section>

Step 4: Admin Registration
---------------------------

Create ``my_blog/admin.py``:

.. code-block:: python

    from django.contrib import admin
    from .models import BlogPost, BlogPostContent

    @admin.register(BlogPost)
    class BlogPostAdmin(admin.ModelAdmin):
        list_display = ("slug",)
        prepopulated_fields = {"slug": ()}

    @admin.register(BlogPostContent)
    class BlogPostContentAdmin(admin.ModelAdmin):
        list_display = ("title", "language", "is_featured", "published_at")
        list_filter = ("language", "is_featured", "published_at")
        prepopulated_fields = {"slug": ("title",)}

Step 5: Configure App
---------------------

Create ``my_blog/apps.py``:

.. code-block:: python

    from django.apps import AppConfig

    class MyBlogConfig(AppConfig):
        default_auto_field = "django.db.models.BigAutoField"
        name = "my_blog"
        verbose_name = "My Blog"

And create ``my_blog/__init__.py`` with:

.. code-block:: python

    default_app_config = "my_blog.apps.MyBlogConfig"

Step 6: Add to Settings
-----------------------

Update ``INSTALLED_APPS``:

.. code-block:: python

    INSTALLED_APPS = [
        # ...
        "djangocms_custom_content",
        "my_blog",
    ]

Step 7: Create and Run Migrations
----------------------------------

.. code-block:: bash

    python manage.py makemigrations my_blog
    python manage.py migrate my_blog

Your blog system is now ready!

Next Steps:

- Learn how to add :doc:`model_with_m2m` to link posts with authors
- Explore :doc:`../how-to/versioning` to track post revisions
- Check :doc:`../how-to/m2m_relations` for more relationship examples
