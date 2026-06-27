Model with M2M Relations
========================

Learn how to create flexible many-to-many relationships between your content
models.

This tutorial builds on the :doc:`article_with_plugins` tutorial.

Overview
--------

We'll add authors to our articles using a
:class:`~djangocms_custom_content.relations.RelationField`:

- Create a ``Person`` grouper/content pair to represent authors
- Declare an ``authors`` relation on the ``Article`` grouper
- Display authors on article pages

The key idea: relations are declared on the **grouper** (``Article``), target
another **grouper** (``Person``), and are anchored to stable primary keys so
they survive versioning.

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

Step 2: Declare the authors relation on Article
------------------------------------------------

Add a ``RelationField`` to the ``Article`` **grouper** (not ``ArticleContent``).
The relation targets ``Person`` and invites a reverse ``authored_articles``
accessor onto it:

.. code-block:: python

    from djangocms_custom_content.relations import RelationField

    class Article(AbstractCustomGrouper):
        """Groups all language versions of an article."""
        authors = RelationField(
            "my_content.Person",
            related_name="authored_articles",
            ordered=True,
        )

``ordered=True`` keeps authors in a stored order and enables ``reorder()``.
``ArticleContent`` is unchanged from the previous tutorials.

Step 3: Register Person with Admin
-----------------------------------

Add to ``my_content/admin.py``:

``Person`` is a grouper, so register it with the grouper admin pattern (see
:doc:`../how-to/admin`). For the ``authors`` autocomplete on the ``Article``
admin to find people, ``PersonAdmin`` must define ``search_fields``:

.. code-block:: python

    from cms.admin.utils import GrouperModelAdmin
    from django.contrib import admin

    from djangocms_custom_content.admin import CustomGrouperAdminMixin
    from .models import Person, PersonContent

    @admin.register(Person)
    class PersonAdmin(CustomGrouperAdminMixin, GrouperModelAdmin):
        content_model = PersonContent
        list_display = ("content__full_name", "content__email")
        search_fields = ("content__full_name", "content__email")

Step 4: Update Article Detail Template with Authors
----------------------------------------------------

The generic detail view renders an ``ArticleContent`` object, available in the
template under its model name, ``articlecontent`` (see :doc:`../how-to/apphooks`).
Reach its grouper through the ``article`` foreign key, then the ``authors``
relation. Each related ``Person`` is a grouper, so read its profile via
``get_admin_content``:

.. code-block:: django

    {% extends "base.html" %}
    {% load cms_tags %}

    {% block content %}
        {% cms_edit_on %}
        <article class="article">
            <h1>{{ articlecontent.title }}</h1>

            {% with authors=articlecontent.article.authors.all %}
                {% if authors %}
                    <div class="authors">
                        <h3>Authors</h3>
                        <ul class="author-list">
                            {% for person in authors %}
                                {% with profile=person.get_admin_content %}
                                    <li class="author">
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
                                            {% if profile.email %}
                                                <p><a href="mailto:{{ profile.email }}">{{ profile.email }}</a></p>
                                            {% endif %}
                                        </div>
                                    </li>
                                {% endwith %}
                            {% endfor %}
                        </ul>
                    </div>
                {% endif %}
            {% endwith %}

            <div class="content">
                {{ articlecontent.body|safe }}
            </div>
        </article>
        {% cms_edit_off %}
    {% endblock %}

Step 5: Create Migrations
--------------------------

.. code-block:: bash

    python manage.py makemigrations my_content
    python manage.py migrate my_content

Step 6: Link Authors to Articles
---------------------------------

Via Django shell:

.. code-block:: python

    from my_content.models import Article, Person

    article = Article.objects.first()   # the grouper
    person = Person.objects.first()

    # Add an author (accepts a Person grouper or a PersonContent)
    article.authors.add(person)

    # Get all authors of an article
    all_authors = article.authors.all()

    # Set an explicit order (relation is ordered)
    article.authors.reorder([person])

    # Remove an author
    article.authors.remove(person)

    # Clear all authors
    article.authors.clear()

Via Django admin:

1. Edit an ``Article`` object (the grouper)
2. Use the ``authors`` autocomplete field to add/remove Person objects
3. Save

Key Concepts
------------

**RelationField**

Declaring ``authors = RelationField("my_content.Person", ...)`` on ``Article``:

- Creates a dedicated through table anchored to grouper primary keys
- Installs a forward ``authors`` accessor on ``Article``
- Installs a reverse ``authored_articles`` accessor on ``Person`` (because of
  ``related_name``) — ``Person`` declares nothing itself

.. code-block:: python

    article.authors.all()        # Person groupers for this article
    person.authored_articles.all()  # Article groupers by this person

**Why the grouper?**

- One Person can be linked to many Articles, and vice versa
- The same Person grouper can be targeted by other content types too
- Because edges store grouper primary keys, they survive version copies

Next Steps
----------

- Learn more in the :doc:`../how-to/m2m_relations` how-to guide
- Explore :doc:`../explanation/relationships` to understand how relations work
  under the hood
- Check :doc:`../reference/index` for the complete API reference
