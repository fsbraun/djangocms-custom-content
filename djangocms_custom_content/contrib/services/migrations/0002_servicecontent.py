"""Split ``Service`` into a grouper and a versioned content model.

``Service`` used to be a plain model holding its own fields. Versioning and frontend
editing need the grouper/content pattern, so the fields move to a new ``ServiceContent``
and ``Service`` becomes the stable identity that plugins point at.

The field values of existing services are carried over. Their *versions* are not created
here: the ``Version`` table belongs to djangocms-versioning, and nothing orders that
app's migrations before this one, so the table may not exist yet while this runs. A
``post_migrate`` receiver (see ``handlers.py``) publishes the migrated content once every
migration in the run has been applied.

The migration is **not reversible**: unapplying it would re-add ``title`` and ``slug``
to ``Service`` as ``NOT NULL`` columns with no default *before* a data migration could
refill them, which fails on any database holding services. Restore from a backup
instead.
"""

import django.db.models.deletion
from django.db import migrations, models

import djangocms_custom_content.models


def move_fields_to_content(apps, schema_editor):
    """Copy each service's fields onto a content object."""
    Service = apps.get_model("djangocms_custom_content_services", "Service")
    ServiceContent = apps.get_model("djangocms_custom_content_services", "ServiceContent")

    ServiceContent.objects.bulk_create(
        ServiceContent(
            service=service,
            title=service.title,
            slug=service.slug,
            summary=service.summary,
            description=service.description,
            is_featured=service.is_featured,
        )
        for service in Service.objects.all()
    )


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
