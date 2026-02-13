Implement Content Versioning
============================

djangocms-custom-content uses language codes to manage multiple versions of content.

Language-Based Versioning
--------------------------

Each content model stores different language variants:

.. code-block:: python

    from my_app.models import Article, ArticleContent

    # Create article
    article = Article.objects.create(name="Article")

    # English version
    content_en = ArticleContent.objects.create(
        article=article,
        language="en",
        title="English Title",
        content="English content",
    )

    # German version
    content_de = ArticleContent.objects.create(
        article=article,
        language="de",
        title="German Titel",
        content="German Inhalt",
    )

    # Retrieve by language
    english = article.get_content(language="en")
    german = article.get_content(language="de")

Creating a Version History Model
--------------------------------

Add a version history model for tracking changes:

.. code-block:: python

    from django.db import models
    from my_app.models import ArticleContent

    class ArticleVersion(models.Model):
        """Historical snapshot of article content."""
        content = models.ForeignKey(ArticleContent, on_delete=models.CASCADE)
        version_number = models.IntegerField()
        title = models.CharField(max_length=200)
        text = models.TextField()
        created_at = models.DateTimeField(auto_now_add=True)
        created_by = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True)
        change_summary = models.CharField(max_length=500, blank=True)

        class Meta:
            ordering = ["-version_number"]
            unique_together = [("content", "version_number")]

        def __str__(self):
            return f"{self.content.title} v{self.version_number}"

Track versions on save:

.. code-block:: python

    from django.db.models.signals import pre_save, post_save
    from django.dispatch import receiver

    @receiver(pre_save, sender=ArticleContent)
    def create_version_on_save(sender, instance, **kwargs):
        """Create a version before saving changes."""
        if instance.pk:
            # Model is being updated
            latest = ArticleVersion.objects.filter(
                content=instance
            ).order_by("-version_number").first()

            next_version = (latest.version_number + 1) if latest else 1

            # Store old content for version record
            old_obj = ArticleContent.objects.get(pk=instance.pk)

            ArticleVersion.objects.create(
                content=old_obj,
                version_number=next_version,
                title=old_obj.title,
                text=old_obj.content,
            )

Retrieve Version History
------------------------

.. code-block:: python

    # Get all versions of a content
    article = ArticleContent.objects.first()
    versions = ArticleVersion.objects.filter(content=article)

    # Display versions
    for v in versions:
        print(f"{v.version_number}: {v.title} ({v.created_at})")

    # Get specific version
    v2 = ArticleVersion.objects.get(content=article, version_number=2)
    print(v2.text)

Display in Admin
----------------

Show version history inline:

.. code-block:: python

    from django.contrib import admin

    class ArticleVersionInline(admin.TabularInline):
        model = ArticleVersion
        extra = 0
        readonly_fields = ("version_number", "created_at", "created_by")
        can_delete = False

    class ArticleContentAdmin(admin.ModelAdmin):
        inlines = [ArticleVersionInline]

    admin.site.register(ArticleContent, ArticleContentAdmin)

Key Points
----------

- Use ``language`` field for multi-language versions
- Use ``get_content(language="xx")`` to retrieve content in specific language
- Create custom version history model for audit trails
- Use Django signals to automatically create versions
- Make version models read-only in admin

See Also
--------

- :doc:`../reference/index` - API reference
- :doc:`../tutorials/basic_setup` - Getting started
