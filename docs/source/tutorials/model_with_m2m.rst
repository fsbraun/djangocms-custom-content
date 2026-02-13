Model with M2M Relations Tutorial
==================================

Learn how to create flexible many-to-many relationships between your content models.

This tutorial builds on the :doc:`blog_example` tutorial.

Overview
--------

We'll add authors to our blog posts using the ``m2m_relations`` feature:

- Create a ``Person`` model to represent authors
- Link ``Person`` objects to blog posts using generic M2M relations
- Display authors on blog post pages

Step 1: Create the Person Model
--------------------------------

Add to ``my_blog/models.py``:

.. code-block:: python

    from djangocms_custom_content.models import (
        AbstractCustomGrouper,
        AbstractCustomContent,
        custom_relation_factory,
    )

    class Person(AbstractCustomGrouper):
        """An author or contributor."""
        class Meta:
            verbose_name = "Author"
            verbose_name_plural = "Authors"

        def __str__(self):
            return self.name

    class PersonContent(AbstractCustomContent):
        """Author profile information."""
        person = models.ForeignKey(Person, on_delete=models.CASCADE)
        full_name = models.CharField(max_length=200)
        bio = models.TextField(blank=True)
        avatar = models.ImageField(upload_to="authors/", null=True, blank=True)
        email = models.EmailField(blank=True)

        class CMSConfig:
            # Add 'author_set' accessor to BlogPost
            m2m_relations = [("author_set", "my_blog.BlogPost")]

        def __str__(self):
            return self.full_name

    # THIS IS REQUIRED for m2m_relations to work
    PersonRelation = custom_relation_factory(PersonContent)

Step 2: Register with Admin
----------------------------

Add to ``my_blog/admin.py``:

.. code-block:: python

    from .models import Person, PersonContent

    @admin.register(Person)
    class PersonAdmin(admin.ModelAdmin):
        list_display = ("id",)

    @admin.register(PersonContent)
    class PersonContentAdmin(admin.ModelAdmin):
        list_display = ("full_name", "email")

Step 3: Use M2M Relations in Views
-----------------------------------

Add to ``my_blog/views.py``:

.. code-block:: python

    from django.shortcuts import render, get_object_or_404
    from .models import BlogPost, BlogPostContent

    def blog_post_detail(request, slug):
        """Display a blog post with its authors."""
        blog_post = get_object_or_404(BlogPost, slug=slug)
        content = blog_post.get_content(request.LANGUAGE_CODE)

        # Get all authors linked to this post
        authors = blog_post.author_set.all()

        return render(
            request,
            "my_blog/post_detail.html",
            {
                "post": content,
                "authors": authors,
            }
        )

Step 4: Create Template with Authors
-------------------------------------

Update ``my_blog/templates/my_blog/post_detail.html``:

.. code-block:: django

    <article class="blog-post">
        <h1>{{ post.title }}</h1>

        <div class="post-meta">
            <time>{{ post.published_at|date:"F j, Y" }}</time>
        </div>

        <div class="authors">
            <h3>Authors</h3>
            <ul>
                {% for author in authors %}
                    <li>
                        {% if author.avatar %}
                            <img src="{{ author.avatar.url }}" alt="{{ author.full_name }}">
                        {% endif %}
                        <div>
                            <strong>{{ author.full_name }}</strong>
                            {% if author.email %}
                                <p><a href="mailto:{{ author.email }}">{{ author.email }}</a></p>
                            {% endif %}
                            <p>{{ author.bio }}</p>
                        </div>
                    </li>
                {% endfor %}
            </ul>
        </div>

        <div class="content">
            {{ post.body|safe }}
        </div>
    </article>

Step 5: Create Migrations
--------------------------

.. code-block:: bash

    python manage.py makemigrations my_blog
    python manage.py migrate my_blog

Step 6: Link Authors to Posts
------------------------------

Via Django shell:

.. code-block:: python

    from my_blog.models import BlogPost, PersonContent

    blog_post = BlogPost.objects.first()
    author = PersonContent.objects.first()

    # Add an author to the post
    blog_post.author_set.add(author)

    # Get all authors of a post
    all_authors = blog_post.author_set.all()

    # Remove an author
    blog_post.author_set.remove(author)

    # Clear all authors
    blog_post.author_set.clear()

Or via Django admin by using the ``PersonContent`` model and adding relationships through the relation model.

Next Steps:

- Learn more about :doc:`../how-to/m2m_relations`
- Explore :doc:`../explanation/architecture` to understand how M2M relations work
- Check :doc:`../reference/index` for complete API reference
