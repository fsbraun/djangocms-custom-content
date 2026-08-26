"""Split ``Service`` into a grouper and a versioned content model.

``Service`` used to be a plain model holding its own fields. Versioning and frontend
editing need the grouper/content pattern, so the fields move to a new ``ServiceContent``
and ``Service`` becomes the stable identity that plugins point at.

The field values of existing services are carried over. Where djangocms-versioning is
installed, each migrated row also gets a published version, so services that were
visible before the migration stay visible after it -- content without a version is
excluded from both the frontend and the admin listings.

The migration is **not reversible**: unapplying it would re-add ``title`` and ``slug``
to ``Service`` as ``NOT NULL`` columns with no default *before* a data migration could
refill them, which fails on any database holding services. Restore from a backup
instead.
"""

import django.db.models.deletion
from django.db import migrations, models

import djangocms_custom_content.models


def move_fields_to_content(apps, schema_editor):
    """Copy each service's fields into a content object and version it."""
    Service = apps.get_model("djangocms_custom_content_services", "Service")
    ServiceContent = apps.get_model("djangocms_custom_content_services", "ServiceContent")

    contents = [
        ServiceContent(
            service=service,
            title=service.title,
            slug=service.slug,
            summary=service.summary,
            description=service.description,
            is_featured=service.is_featured,
        )
        for service in Service.objects.all()
    ]
    if not contents:
        return
    ServiceContent.objects.bulk_create(contents)
    _create_published_versions(list(ServiceContent.objects.values_list("pk", flat=True)))


def _create_published_versions(content_pks):
    """Give each migrated content object a published version.

    Works on the real (not historical) models throughout: version numbering and the
    state machine live on ``Version.save()``, and ``Version`` resolves its versionable
    from the content class -- neither of which a ``__fake__`` historical model carries.
    Silently does nothing when djangocms-versioning is not installed, or when the
    database holds no user to attribute the version to; an unversioned content object is
    a state django CMS already tolerates, and publishing it by hand is a single click.
    """
    from django.apps import apps as django_apps

    if not django_apps.is_installed("djangocms_versioning"):
        return

    from django.contrib.auth import get_user_model
    from djangocms_versioning import constants
    from djangocms_versioning.models import Version

    from djangocms_custom_content.contrib.services.models import ServiceContent

    User = get_user_model()
    author = User.objects.filter(is_superuser=True).order_by("pk").first() or User.objects.order_by("pk").first()
    if author is None:
        return

    # ``_base_manager`` bypasses the published-only filter versioning installs on ``objects``.
    for content in ServiceContent._base_manager.filter(pk__in=content_pks):
        Version.objects.create(content=content, created_by=author, state=constants.PUBLISHED)


class Migration(migrations.Migration):
    dependencies = [
        ("djangocms_custom_content_services", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ServiceContent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200, verbose_name="Title")),
                ("slug", models.SlugField(verbose_name="Slug")),
                ("summary", models.TextField(blank=True, verbose_name="Summary")),
                ("description", models.TextField(blank=True, verbose_name="Description")),
                ("is_featured", models.BooleanField(default=False, verbose_name="Featured")),
                (
                    "service",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="djangocms_custom_content_services.service",
                    ),
                ),
            ],
            options={
                "verbose_name": "Service",
                "verbose_name_plural": "Services",
                "ordering": ("title",),
            },
            bases=(djangocms_custom_content.models.CustomContentMixin, models.Model),
        ),
        # Carry the data over before the columns it lives in are dropped. No reverse: see
        # the module docstring.
        migrations.RunPython(move_fields_to_content),
        migrations.RemoveField(model_name="service", name="title"),
        migrations.RemoveField(model_name="service", name="slug"),
        migrations.RemoveField(model_name="service", name="summary"),
        migrations.RemoveField(model_name="service", name="description"),
        migrations.RemoveField(model_name="service", name="is_featured"),
        migrations.AlterModelOptions(name="service", options={}),
    ]
