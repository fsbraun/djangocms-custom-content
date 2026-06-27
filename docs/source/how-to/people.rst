Using the contrib.people module
===============================

Manage people/authors and link them to content via M2M relations.

Installation
------------

.. code-block:: python

    INSTALLED_APPS = [
        "djangocms_custom_content",
        "djangocms_custom_content.contrib.people",
    ]

.. code-block:: bash

    python manage.py migrate

Models
------

**Person** - The grouper. Optionally linked to a ``User`` via a one-to-one field.
**PersonContent** - The versioned content holding the person's details

Content fields: ``name``, ``slug``, ``role``, ``description``, ``phone``,
``mobile``, ``fax``, ``email``, ``website``, ``visual`` (a Filer image).

Usage
-----

Creating people:

.. code-block:: python

    from djangocms_custom_content.contrib.people.models import Person, PersonContent

    person = Person.objects.create()
    PersonContent.objects.create(
        person=person,
        slug="john-doe",
        name="John Doe",
        role="Author",
        description="Author bio...",
    )

Linking people as authors:

People are linked through a ``RelationField`` declared on the *grouper* that
wants authors. The bundled blog does exactly this on ``BlogPost`` (see
``contrib/blog/models.py``):

.. code-block:: python

    class BlogPost(AbstractCustomGrouper):
        authors = RelationField(
            "djangocms_custom_content_people.Person",
            related_name="authored_posts",
            ordered=True,
        )

.. code-block:: python

    blog_post = BlogPost.objects.first()
    blog_post.authors.add(person)   # accepts a Person grouper or PersonContent
    blog_post.authors.all()         # Person groupers, in their stored order

    # Reverse accessor invited by related_name:
    person.authored_posts.all()     # BlogPost groupers authored by this person

In templates (``authors.all`` yields ``Person`` groupers, so reach the content
via ``get_admin_content``):

.. code-block:: django

    {% for person in blog_post.authors.all %}
        {% with profile=person.get_admin_content %}
            <div class="author">
                <h4>{{ profile.name }}</h4>
                <p>{{ profile.description }}</p>
            </div>
        {% endwith %}
    {% endfor %}

Plugins
-------

- ``PersonTeaserPlugin`` ("Person teaser", model ``PersonTeaser``) - Display a
  single selected person, with an optional bio toggle

Admin
-----

Registered in Django admin as a grouper admin.

See Also
--------

- :doc:`../how-to/m2m_relations` - M2M relations guide
- :doc:`../tutorials/model_with_m2m` - Tutorial with Person example
