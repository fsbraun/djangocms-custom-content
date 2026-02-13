People Module (Authors)
=======================

Manage people/authors and link them to content via M2M relations.

Installation
-----------

.. code-block:: python

    INSTALLED_APPS = [
        "djangocms_custom_content",
        "djangocms_custom_content.contrib.people",
    ]

.. code-block:: bash

    python manage.py migrate

Models
------

**Person** - Groups all language versions of a person
**PersonContent** - Language-specific person information (name, bio, etc.)

Usage
-----

Creating people:

.. code-block:: python

    from djangocms_custom_content.contrib.people.models import Person, PersonContent

    person = Person.objects.create()
    PersonContent.objects.create(
        person=person,
        language="en",
        first_name="John",
        last_name="Doe",
        bio="Author bio...",
    )

Linking to content:

.. code-block:: python

    # In your BlogPost model
    class CMSConfig:
        m2m_relations = [("authors", "blog.BlogPost")]

    # Use it
    blog_post = BlogPost.objects.first()
    blog_post.authors.all()  # Get all authors
    blog_post.authors.add(person_content)

In templates:

.. code-block:: django

    {% for person in article.authors.all %}
        <div class="author">
            <h4>{{ person.first_name }} {{ person.last_name }}</h4>
            <p>{{ person.bio }}</p>
        </div>
    {% endfor %}

Plugins
-------

``PersonTeaser`` - Display a single person
``PersonList`` - Display a list of people

Admin
-----

Registered in Django admin with inline editing.

See Also
--------

- :doc:`../how-to/m2m_relations` - M2M relations guide
- :doc:`../tutorials/model_with_m2m` - Tutorial with Person example
