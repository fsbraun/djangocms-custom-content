Model with M2M Relations Tutorial
==================================

Learn how to create flexible many-to-many relationships between your content models.

This tutorial builds on the :doc:`article_with_plugins` tutorial.

Overview
--------

We'll add authors to our articles using the ``invite_m2m_relations`` feature:

- Create a ``Person`` model to represent authors
- Link ``Person`` objects to articles using generic M2M relations
- Display authors on article pages

Step 1: Create the Person Model
--------------------------------

Add to ``my_content/models.py``:

.. code-block:: python

    from django.db import models
    from djangocms_custom_content.models import (
        AbstractCustomGrouper,
        AbstractCustomContent,
        custom_relation_factory,
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

    # THIS IS REQUIRED for invite_m2m_relations to work
    # Note: Create relation factory for the Grouper (Person), not Content model
    PersonRelation = custom_relation_factory(Person)

Step 2: Configure ArticleContent for M2M
------------------------------------------

Update the ``ArticleContent`` model in ``my_content/models.py`` to point to Person:

.. code-block:: python

    class ArticleContent(AbstractCustomContent):
        """The editable article content."""
        article = models.ForeignKey(Article, on_delete=models.CASCADE)
        title = models.CharField(max_length=200)
        slug = models.SlugField()
        body = models.TextField()

        class CMSConfig:
            editable = True
            versionable = True
            apphook = True
            # Request authors from the Person model
            invite_m2m_relations = [("authors", "my_content.Person")]

        def __str__(self):
            return self.title

        def __str__(self):
            return self.title

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

Step 4: Update Article Detail Template with Authors
----------------------------------------------------

Update ``my_content/templates/my_content/article_detail.html`` to display authors.
The generic detail view automatically provides the article object and you can access authors via the ``invite_m2m_relations`` accessor:

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
                                {% if author.avatar %}
                                    <img src="{{ author.avatar.url }}"
                                         alt="{{ author.full_name }}"
                                         class="author-avatar">
                                {% endif %}
                                <div class="author-info">
                                    <strong>{{ author.full_name }}</strong>
                                    {% if author.bio %}
                                        <p class="bio">{{ author.bio }}</p>
                                    {% endif %}
                                    {% if author.email %}
                                        <p><a href="mailto:{{ author.email }}">{{ author.email }}</a></p>
                                    {% endif %}
                                </div>
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

Step 6: Link Authors to Articles
---------------------------------

Via Django shell:

.. code-block:: python

    from my_content.models import ArticleContent, Person

    article = ArticleContent.objects.first()
    person = Person.objects.first()

    # Add an author to the article
    article.authors.add(person)

    # Get all authors of an article
    all_authors = article.authors.all()

    # Remove an author
    article.authors.remove(person)

    # Clear all authors
    article.authors.clear()

Via Django admin:

1. Edit an ``ArticleContent`` object
2. Use the ``authors`` accessor to add/remove Person objects
3. Save

Key Concepts
-----------

**invite_m2m_relations**

The ``invite_m2m_relations`` configuration tells ArticleContent:

- "I want to link to Person objects"
- "Please add an ``authors`` accessor to my instances"
- "Use a generic through model to handle the relationship"

This creates a bidirectional relationship:

.. code-block:: python

    # From ArticleContent side:
    article.authors.all()  # Get authors of this article

    # There's no direct reverse accessor on Person
    # (it doesn't know about articles)

**Generic M2M Benefits**

- One Person can be linked to many ArticleContent instances
- The same Person model can be linked to other content types without modification
- The through model (PersonRelation) is shared across all relations

Next Steps
----------

- Learn more about :doc:`../how-to/m2m_relations` and the difference between ``relate_to`` and ``invite_m2m_relations``
- Explore :doc:`../explanation/relationships` to understand how generic M2M relations work under the hood
- Check :doc:`../reference/index` for complete API reference
