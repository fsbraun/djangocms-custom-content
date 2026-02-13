Set Up Many-to-Many Relations
=============================

djangocms-custom-content provides two complementary approaches for managing M2M relationships:

1. **``invite_m2m_relations``** - Content model requests relations from target models
2. **``relate_to``** - Model pushes relations onto target models

Understanding the Direction
----------------------------

The key difference is **who initiates the relationship**:

**``invite_m2m_relations`` (Content Model → Target Model)**

- The source model **knows about** and **requests** relations from target models
- If the target model is not installed or lacks a relation model, a dummy accessor
  is created (graceful degradation)
- Typical use: A content model inviting a grouper model to participate

**``relate_to`` (Model → Unknown Targets)**

- The source model **pushes** itself onto target models
- Target models are unaware of the source and its configuration
- The source unilaterally adds accessors to target models
- Typical use: A model relating to multiple content types, including
  already installed ones.
- Since the target model does not know about the source, it will not copy
  the relation when copied. Hence avoid using ``relate_to`` to relate to
  potentially versioned content models, since they are copied regularly when
  new versions are created.

Example Comparison
------------------

**Scenario: BlogPostContent wants authors**

Using ``invite_m2m_relations`` (content model requests):

.. code-block:: python

    class BlogPostContent(AbstractCustomContent):
        class CMSConfig:
            # "I invite Person to give me authors"
            invite_m2m_relations = [("authors", "my_app.Person")]

The source knows: "I want authors from Person". ``Person`` needs to provide
the m2m relation through model.

Result: ``blog_post_content.authors.add(person)``


**Scenario: FlatCategory relates to BlogPost**

Using ``relate_to`` (model pushes to target):

.. code-block:: python

    class FlatCategory(AbstractCustomContent):
        class CMSConfig:
            # "I'm adding categories accessor to BlogPost"
            relate_to = [("categories", "my_app.BlogPost")]

    FlatCategoryRelation = custom_relation_factory(FlatCategory)

The ``BlogPost`` doesn't know about ``FlatCategory`` internals. ``FlatCategory`` has
to provide the m2m relation through model.

Result: ``blog_post.categories.add(category)``


Approach 1: Using ``invite_m2m_relations`` (Content Model Requests)
------------------------------------------------------------------

Use ``invite_m2m_relations`` when:

- Your content model knows about and depends on target models
- You want graceful handling if targets are not available
- Target models should provide a specific relation interface

**Example: BlogPostContent inviting authors from Person**

.. code-block:: python

    from djangocms_custom_content.models import (
        AbstractCustomContent,
        custom_relation_factory,
    )

    class BlogPostContent(AbstractCustomContent):
        """Blog post content with versioning."""
        post = models.ForeignKey("my_app.BlogPost", on_delete=models.CASCADE)
        title = models.CharField(max_length=200)
        body = models.TextField()

        class CMSConfig:
            enable_versioning = True
            # Invite authors from Person model
            invite_m2m_relations = [
                ("authors", "my_app.Person"),
            ]

        def __str__(self):
            return self.title


Usage:

.. code-block:: python

    blog_post_content = BlogPostContent.objects.first()
    person = Person.objects.first()

    blog_post_content.authors.add(person)
    blog_post_content.authors.all()  # QuerySet of Person objects

**Graceful Degradation:**

If ``Person`` model is not installed or lacks a relation model, ``invite_m2m_relations`` creates a dummy accessor that returns empty querysets instead of failing.


Approach 2: Using ``relate_to`` (Model Pushes to Target)
-------------------------------------------------------

Use ``relate_to`` when:

- Your model should relate to target models independently
- Target models don't need to know about your model
- You want to add accessors to multiple unrelated models

**Example: FlatCategory adding categories to BlogPost**

.. code-block:: python

    class FlatCategory(AbstractCustomContent):
        """A simple category model."""
        title = models.CharField(max_length=100)
        slug = models.SlugField(unique=True)

        class CMSConfig:
            # Push categories accessor to BlogPost
            relate_to = [
                ("categories", "my_app.BlogPost"),
                ("categories", "my_app.Article"),  # Multiple targets possible
            ]

        def __str__(self):
            return self.title

    # Create the relation model (required)
    FlatCategoryRelation = custom_relation_factory(FlatCategory)

Usage:

.. code-block:: python

    blog_post = BlogPost.objects.first()
    category = FlatCategory.objects.first()

    blog_post.categories.add(category)
    blog_post.categories.all()  # QuerySet of FlatCategory objects


Key Differences
---------------

.. list-table::
   :widths: 25 38 37
   :header-rows: 1

   * - Aspect
     - ``invite_m2m_relations``
     - ``relate_to``
   * - Semantic
     - "I request from you"
     - "I push to you"
   * - Initiation
     - Source knows target
     - Source may not know target
   * - Direction
     - Content model → Target
     - Model → Unknown targets
   * - If target unavailable
     - Creates dummy accessor
     - Skips silently (LookupError)
   * - Typical use
     - Authors, Contributors
     - Categories, Tags
   * - Target awareness
     - Target expects source
     - Target unaware of source
   * - Best for
     - Related models with awareness
     - Simple models relating widely


Using the Accessors
-------------------

Both provide identical manager interfaces:

.. code-block:: python

    # add() - Add objects
    model.accessor.add(obj1, obj2)

    # all() - Get all related
    related = model.accessor.all()

    # filter() - Filter related
    related = model.accessor.all().filter(name="Django")

    # remove() - Remove specific
    model.accessor.remove(obj1)

    # clear() - Remove all
    model.accessor.clear()

    # count() - Count relations
    count = model.accessor.all().count()

    # exists() - Check existence
    if model.accessor.all().exists():
        ...

In Templates
~~~~~~~~~~~~

.. code-block:: django

    {# invite_m2m_relations example #}
    {% for author in blog_post_content.authors.all %}
        <strong>{{ author.get_admin_content.name }}</strong>
    {% endfor %}

    {# relate_to example #}
    {% for category in blog_post.categories.all %}
        <span class="category">{{ category.title }}</span>
    {% endfor %}

Multiple Accessors
-------------------

You can define multiple accessors from a single model:

**Multiple targets with ``relate_to``:**

.. code-block:: python

    class Tag(AbstractCustomContent):
        name = models.CharField(max_length=100)

        class CMSConfig:
            relate_to = [
                ("tags", "blog.BlogPost"),
                ("tags", "article.Article"),
                ("tags", "product.Product"),
            ]

    TagRelation = custom_relation_factory(Tag)

**Multiple accessors from different target with ``invite_m2m_relations``:**

.. code-block:: python

    class PersonContent(AbstractCustomContent):
        class CMSConfig:
            invite_m2m_relations = [
                ("authors", "blog.BlogPost"),
                ("reviewers", "article.Article"),
            ]



When to Use Which
-----------------

**Use ``invite_m2m_relations`` when:**

- Your content model needs specific relations
- You want graceful handling of missing targets
- Relations are a desired extension to your model's logic
- Target models are expected to have relation support

**Use ``relate_to`` when:**

- You want to add relations to models you don't control
- The source model should work independently
- You're adding a cross-cutting concern (categories, tags)
- Target models shouldn't need to know about your model


See Also
--------

- :doc:`../reference/index` - API reference
- :doc:`../explanation/relationships` - Relationship architecture
- :doc:`../tutorials/model_with_m2m` - Step-by-step tutorial
