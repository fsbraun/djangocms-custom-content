M2M Relationships Explained
===========================

djangocms-custom-content provides flexible many-to-many relationships through two approaches that differ in **direction and semantics**:

1. ``invite_m2m_relations`` - Content model **requests** relations from target models (pull)
2. ``relate_to`` - Model **pushes** relations onto target models (push)

The Through Model: ``custom_relation_factory``
-----------------------------------------------

Traditional M2M relationships in Django use an **automatic through model** (join table) that links two specific models:

.. code-block:: python

    # Standard Django M2M
    class Article(models.Model):
        authors = models.ManyToManyField(Author)  # Creates automatic through model

The through model has two ForeignKeys (one to each side).

**Problem:** This only works for relating to ONE specific model type. You can't use one M2M field for relating to different model types.

**Solution:** ``custom_relation_factory``

djangocms-custom-content creates a **manual through model** that uses:

- **One ForeignKey** to the source model (specific)
- **One GenericForeignKey** to ANY model (flexible)

This enables relating a source model to objects of ANY type.

**How it Works**

.. code-block:: python

    from djangocms_custom_content.models import custom_relation_factory

    class PersonContent(AbstractCustomContent):
        person = models.ForeignKey(Person, on_delete=models.CASCADE)
        # ... other fields ...

    # Manually create the through model for the Grouper (Person)
    PersonRelation = custom_relation_factory(Person)

**Generated Through Model Structure**

The ``custom_relation_factory`` creates a relation model like:

.. code-block:: python

    class PersonContentRelation(AbstractCustomRelation):
        # FK to source (specific model)
        instance = models.ForeignKey(PersonContent, on_delete=models.CASCADE)

        # Can relate to ANY model
        content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
        object_id = models.PositiveIntegerField()
        content_object = GenericForeignKey('content_type', 'object_id')

**The GenericForeignKey Magic**

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Field
     - Purpose
   * - ``instance``
     - FK to PersonContent (always the same model)
   * - ``content_type``
     - Stores which model type is related (BlogPost, Article, etc.)
   * - ``object_id``
     - Stores the ID of the related object
   * - ``content_object``
     - Virtual field that returns the actual object (BlogPost #5, Article #3, etc.)

**Example Data**

One ``PersonContentRelation`` table can store relations to MULTIPLE model types:

.. code-block:: sql

    -- Person 2 as author of BlogPost 1
    INSERT INTO person_content_relation
      (instance_id, content_type_id, object_id)
    VALUES (2, 42, 1);  -- content_type_id 42 = BlogPost

    -- Person 2 as author of Article 5
    INSERT INTO person_content_relation
      (instance_id, content_type_id, object_id)
    VALUES (2, 43, 5);  -- content_type_id 43 = Article

    -- Person 2 as author of Product 3
    INSERT INTO person_content_relation
      (instance_id, content_type_id, object_id)
    VALUES (2, 44, 3);  -- content_type_id 44 = Product

**Single PersonContent can relate to thousands of BlogPosts, Articles, Products, etc.**

Comparison: Django M2M vs. Generic M2M
--------------------------------------

.. list-table::
   :widths: 30 35 35
   :header-rows: 1

   * - Aspect
     - Standard Django M2M
     - Generic M2M (via custom_relation_factory)
   * - Through model
     - Auto-generated
     - Manually generated
   * - Flexibility
     - Fixed to one model pair
     - Can relate to ANY model
     - Reusability
     - Each M2M needs separate field
     - One through model relates to all targets
   * - ForeignKey 1
     - ForeignKey to Model A
     - ForeignKey to source
   * - ForeignKey 2
     - ForeignKey to Model B
     - GenericForeignKey (ANY model)
   * - Storage
     - Separate table per relationship
     - Single generic table
   * - Use case
     - Simple one-to-one M2M
     - Multi-target relations

Django M2M Example
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Separate through models needed for each relation type
    class BlogPost(models.Model):
        authors = models.ManyToManyField(Person)      # Through: BlogPost_authors

    class Article(models.Model):
        authors = models.ManyToManyField(Person)      # Through: Article_authors

    class Product(models.Model):
        creators = models.ManyToManyField(Person)     # Through: Product_creators

**Result:** Three separate though tables, each only works for its specific pair.

Generic M2M Example
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    class PersonContent(AbstractCustomContent):
        pass

    # Single through model for ALL relations
    # Note: Factory is created for the Grouper (Person), not the Content model
    PersonRelation = custom_relation_factory(Person)

    # PersonRelation table can manage relations to:
    # - BlogPost
    # - Article
    # - Product
    # - ANY Django model

**Result:** One table handles all relations!

How the Two Approaches Use ``custom_relation_factory``
-------------------------------------------------------

Both ``relate_to`` and ``invite_m2m_relations`` use the through model created by ``custom_relation_factory``:

**``invite_m2m_relations`` (Content Model Requests)**

The source model **knows about** and **requests** relations from target models.

**Semantics:** "I invite you to provide relations for me. Do you have a suitable generic through table?"

**Direction:** Known target → Source

**Flow:**

1. Source model declares ``invite_m2m_relations`` listing targets
2. ``custom_relation_factory`` creates through model for source
3. CustomContentExtension reads the declaration
4. GenericM2MDescriptor is added to SOURCE model (not target)
5. If target unavailable: Creates dummy accessor (graceful degradation)

**Example:**

.. code-block:: python

    class BlogPostContent(AbstractCustomContent):
        class CMSConfig:
            # "I request relations from Person"
            invite_m2m_relations = [("authors", "people.Person")]

    # Creates the through model with GenericForeignKey
    # The factory is for the target model (Person), not the source
    PersonRelation = custom_relation_factory(Person)

**Result:**

.. code-block:: python

    blog_post = BlogPostContent.objects.first()
    person = Person.objects.first()

    # Source model gets the accessor (via GenericM2MDescriptor)
    blog_post.authors.add(person)
    blog_post.authors.all()  # Uses PersonRelation table


Approach 2: ``relate_to`` (Model Pushes to Targets)
---------------------------------------------------

The source model **pushes** itself onto target models you have no control over.

**Semantics:** "I'm adding an accessor to you, so you can see me."

**Direction:** Source → Multiple unknown targets

**Flow:**

1. Source model declares ``relate_to`` listing target paths
2. ``custom_relation_factory`` creates through model for source
3. ``register_m2m_relations()`` is called
4. GenericM2MDescriptor is added to TARGET models (not source)
5. Target models remain unaware of source

**Example:**

.. code-block:: python

    class FlatCategory(AbstractCustomContent):
        class CMSConfig:
            # "I'm adding categories accessor to BlogPost and Article"
            relate_to = [
                ("categories", "blog.BlogPost"),
                ("categories", "article.Article"),
            ]

    # Creates the through model with GenericForeignKey
    FlatCategoryRelation = custom_relation_factory(FlatCategory)

**Result:**

.. code-block:: python

    blog_post = BlogPost.objects.first()
    article = Article.objects.first()
    category = FlatCategory.objects.first()

    # Target models get the accessor (via GenericM2MDescriptor)
    blog_post.categories.add(category)
    article.categories.add(category)

    # Both use same FlatCategoryRelation table!


Design Differences
------------------

.. list-table::
   :widths: 20 40 40
   :header-rows: 1

   * - Aspect
     - ``invite_m2m_relations``
     - ``relate_to``
   * - Who requests
     - TARGET model
     - SOURCE model
   * - Semantics
     - "I request from you"
     - "I push to you"
   * - Accessor added to
     - TARGET model
     - TARGET model(s)
   * - Source awareness
     - Unaware of target
     - Knows target
   * - Target awareness
     - Expected to support it
     - Unaware of source
   * - If target unavailable
     - Dummy accessor created
     - Raises improperly configured exception
   * - Typical sources
     - Grouper models
     - Grouper models
   * - Typical targets
     - Content models
     - Content models


Accessing Relations
-------------------

Both provide identical manager interfaces (backed by the through model):

.. code-block:: python

    # add() - Add objects
    model.accessor.add(obj1, obj2)

    # all() - Get all related
    related = model.accessor.all()

    # filter() - Filter related
    related = model.accessor.filter(name="Django")

    # remove() - Remove specific
    model.accessor.remove(obj1)

    # clear() - Remove all
    model.accessor.clear()

    # count() - Count relations
    count = model.accessor.count()

    # exists() - Check existence
    if model.accessor.exists():
        ...

See Also
--------

- :doc:`../how-to/m2m_relations` - Practical implementation guide
- :doc:`../tutorials/model_with_m2m` - Step-by-step tutorial
- :doc:`../reference/index` - API reference
