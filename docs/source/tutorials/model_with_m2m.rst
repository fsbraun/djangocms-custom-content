Model with M2M Relations
========================

Learn how to add many-to-many relationships between your content models using
the declarative ``CMSConfig.m2m`` API.

This tutorial builds on the :doc:`article_with_plugins` tutorial.

Overview
--------

We'll add authors to articles in a single line of configuration:

- Create a ``Person`` grouper to represent authors
- Declare an ``authors`` relation on ``ArticleContent``
- Display authors on article pages, and articles on author pages

Step 1: Create the Person Model
--------------------------------

Add to ``my_content/models.py``:

.. code-block:: python

    from django.db import models
    from djangocms_custom_content.models import (
        AbstractCustomGrouper,
        AbstractCustomContent,
    )

    # Existing Article and ArticleContent models...
    # (from the basic_setup tutorial)

    class Person(AbstractCustomGrouper):
        """An author or contributor."""
        class Meta:
            verbose_name = "Author"
            verbose_name_plural = "Authors"

        def __str__(self):
            person_content = self.get_admin_content()
            return person_content.full_name if person_content else "Unknown"

    class PersonContent(AbstractCustomContent):
        """Author profile information."""
        person = models.ForeignKey(Person, on_delete=models.CASCADE)
        full_name = models.CharField(max_length=200)
        bio = models.TextField(blank=True)
        avatar = models.ImageField(upload_to="authors/", null=True, blank=True)
        email = models.EmailField(blank=True)

        class CMSConfig:
            enable_versioning = True

        def __str__(self):
            return self.full_name

No relation-table boilerplate is needed: the through-model is generated for
you in step 2 by declaring the relation on ``ArticleContent``.

Step 2: Declare the Relation on ArticleContent
----------------------------------------------

Update the ``ArticleContent`` model in ``my_content/models.py``:

.. code-block:: python

    class ArticleContent(AbstractCustomContent):
        """The editable article content."""
        article = models.ForeignKey(Article, on_delete=models.CASCADE)
        title = models.CharField(max_length=200)
        slug = models.SlugField()
        body = models.TextField()

        class CMSConfig:
            enable_frontend_editing = True
            enable_versioning = True
            apphook = True
            m2m = [
                ("authors", "my_content.Person"),
            ]

        def __str__(self):
            return self.title

That's all — declaring ``m2m`` automatically:

* creates ``ArticleContentRelation`` in the ``my_content`` app
* installs ``Article.authors`` (forward) on the grouper
* installs ``Person.article_set`` (reverse, auto-named) on the target grouper

Step 3: Register Person with Admin
-----------------------------------

Add to ``my_content/admin.py``:

.. code-block:: python

    from .models import Person, PersonContent

    @admin.register(Person)
    class PersonAdmin(admin.ModelAdmin):
        list_display = ("id",)

    @admin.register(PersonContent)
    class PersonContentAdmin(admin.ModelAdmin):
        list_display = ("full_name", "email")

Step 4: Display Authors on the Article Page
-------------------------------------------

Update ``my_content/templates/my_content/article_detail.html``. The forward
accessor lives on the grouper (``Article``), which the detail view exposes as
``article``:

.. code-block:: django

    {% extends "base.html" %}
    {% load cms_tags %}

    {% block content %}
        {% cms_edit_on %}
        <article class="article">
            <h1>{{ article.title }}</h1>

            {% if article.authors.all %}
                <div class="authors">
                    <h3>Authors</h3>
                    <ul class="author-list">
                        {% for author in article.authors.all %}
                            <li class="author">
                                {% with author.get_admin_content as profile %}
                                    {% if profile.avatar %}
                                        <img src="{{ profile.avatar.url }}"
                                             alt="{{ profile.full_name }}"
                                             class="author-avatar">
                                    {% endif %}
                                    <div class="author-info">
                                        <strong>{{ profile.full_name }}</strong>
                                        {% if profile.bio %}
                                            <p class="bio">{{ profile.bio }}</p>
                                        {% endif %}
                                    </div>
                                {% endwith %}
                            </li>
                        {% endfor %}
                    </ul>
                </div>
            {% endif %}

            <div class="content">
                {{ article.body|safe }}
            </div>
        </article>
        {% cms_edit_off %}
    {% endblock %}

Step 5: Create Migrations
--------------------------

.. code-block:: bash

    python manage.py makemigrations my_content
    python manage.py migrate my_content

The generated migration creates the ``Person``/``PersonContent`` models *and*
the auto-generated ``ArticleContentRelation`` through-table in one go.

Step 6: Link Authors to Articles
---------------------------------

Via Django shell:

.. code-block:: python

    from my_content.models import Article, Person

    article = Article.objects.first()
    person = Person.objects.first()

    # Forward — add an author to the article
    article.authors.add(person)

    # Get all authors of an article
    list(article.authors.all())

    # Reverse — get all articles by a person (auto-named accessor)
    list(person.article_set.all())

    # Remove / clear
    article.authors.remove(person)
    article.authors.clear()

Key Concepts
------------

**CMSConfig.m2m**

A single list entry declares both directions of the relation:

.. code-block:: python

    m2m = [("authors", "my_content.Person")]

- Forward accessor ``authors`` installed on the declarer's grouper
  (``Article``).
- Reverse accessor ``article_set`` installed on the target grouper
  (``Person``) — derived from the owner's lowercased model name.

**Auto-generated through-model**

The framework creates ``ArticleContentRelation`` for you. It's a normal Django
model, picked up by ``makemigrations``, with a single ``relation_name`` column
that lets multiple ``m2m`` entries share the same table.

**Language-independent by default**

Because the through-model's FK targets the grouper (not the content), authors
attached to one language version are visible from all language versions.

**Custom reverse names**

Use the 3-tuple form to override the reverse name, or pass ``None`` to
suppress the reverse accessor:

.. code-block:: python

    m2m = [
        ("authors", "my_content.Person", "wrote"),     # person.wrote
        ("reviewers", "my_content.Person", None),      # no reverse on Person
    ]

Next Steps
----------

- Read :doc:`../how-to/m2m_relations` for the full ``m2m`` reference
- Explore :doc:`../explanation/relationships` for the design rationale
- Check :doc:`../reference/index` for the complete API reference
