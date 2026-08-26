"""Post-migrate backfill for services that predate versioning.

``0002_servicecontent`` moves the fields of pre-existing services onto content objects
but deliberately does not create their versions: the ``Version`` table belongs to
djangocms-versioning, and nothing orders that app's migrations before this one, so the
table may not exist yet while the data migration runs.

Content without a version is excluded from both the frontend and the admin listings --
the grouper shows up as "Empty content" and there is no way to recover it through the
UI. The backfill therefore runs from ``post_migrate``, which fires once every migration
in the run has been applied.
"""

import warnings

from django.apps import apps
from django.contrib.auth import get_user_model


def backfill_service_versions(sender, using=None, verbosity=1, **kwargs):
    """Give every unversioned ``ServiceContent`` a published version."""
    if not apps.is_installed("djangocms_versioning"):
        return

    from djangocms_versioning import constants
    from djangocms_versioning.models import Version

    from .models import ServiceContent

    # ``_base_manager`` bypasses the published-only filter versioning installs on
    # ``objects``; ``versions`` is the generic relation versioning adds to content models.
    unversioned = list(ServiceContent._base_manager.using(using).filter(versions__isnull=True))
    if not unversioned:
        return

    author = _pick_author(using)
    if author is None:
        warnings.warn(
            f"{len(unversioned)} service(s) were migrated to versioned content but no user "
            f"exists to attribute a version to, so they have been left unversioned and are "
            f"not visible on the site or in the admin. Create a user and re-run "
            f"`migrate` to publish them.",
            RuntimeWarning,
            stacklevel=2,
        )
        return

    for content in unversioned:
        Version.objects.using(using).create(content=content, created_by=author, state=constants.PUBLISHED)

    if verbosity >= 1:
        print(f"  Published {len(unversioned)} migrated service(s).")


def _pick_author(using):
    """The user a backfilled version is attributed to: a superuser, else any user."""
    users = get_user_model()._base_manager.using(using)
    return users.filter(is_superuser=True).order_by("pk").first() or users.order_by("pk").first()
