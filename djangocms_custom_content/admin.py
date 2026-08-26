from typing import TYPE_CHECKING

from cms.admin.utils import CONTENT_PREFIX
from cms.utils.urlutils import admin_reverse
from django.apps import apps
from django.db import models
from django.http import HttpResponseRedirect
from django.urls import path

from djangocms_custom_content.relation_admin import RelationAdminMixin

if TYPE_CHECKING:
    from django.contrib.admin import AdminSite


class SlugUniquenessFormMixin:
    """Reject a slug already used by another object, on the grouper change form.

    The grouper form edits content fields under a ``content__`` prefix and never
    runs the content model's own ``full_clean()``, so the model-level
    :meth:`~djangocms_custom_content.models.AbstractCustomContent.validate_unique`
    would not fire here. This repeats the check where the admin can attach the
    error to the field the editor typed in.
    """

    def clean(self) -> dict:
        cleaned_data = super().clean()
        slug_field = CONTENT_PREFIX + "slug"
        if slug_field not in cleaned_data or self.has_error(slug_field):
            return cleaned_data

        content_model = self._admin.content_model
        language = cleaned_data.get(CONTENT_PREFIX + "language") or self._admin.current_content_filters.get("language")
        conflicts = content_model.find_slug_conflicts(
            cleaned_data[slug_field],
            language=language,
            # On the add view the grouper has no pk yet, so nothing is excluded.
            grouper_id=self.instance.pk,
        )
        if conflicts.exists():
            self.add_error(slug_field, content_model.slug_conflict_message())
        return cleaned_data


class CustomGrouperAdminMixin(RelationAdminMixin):
    """Admin mixin to redirect content endpoints for grouper admins.

    Provides a breadcrumb redirect compatible with django CMS versioning, and
    (via :class:`RelationAdminMixin`) renders any ``RelationField`` on the model
    as an autocomplete multi-select — sortable when the relation is ordered.

    Prefetching of the latest related content (``_admin_prefetch_cache``) is
    handled by ``cms.admin.utils.GrouperModelAdmin.get_queryset``, which the
    concrete admin classes inherit from, so this mixin does not override
    ``get_queryset``.
    """

    if TYPE_CHECKING:
        # Provided by the ModelAdmin / GrouperModelAdmin this mixin is combined with.
        admin_site: AdminSite
        model: type[models.Model]
        content_model: type[models.Model]

    def get_form(self, request, obj=None, **kwargs):
        """Add slug-uniqueness validation to the grouper change form.

        Injected into the *base* form rather than wrapped around the finished one:
        subclassing a built form re-runs ``ModelFormMetaclass``, which rebuilds
        ``base_fields`` and would discard the autocomplete widgets
        :class:`RelationAdminMixin` has already applied.
        """
        if self.content_model.has_slug_field():
            base_form = kwargs.get("form", self.form)
            if not (isinstance(base_form, type) and issubclass(base_form, SlugUniquenessFormMixin)):
                kwargs["form"] = type("SlugUniquenessForm", (SlugUniquenessFormMixin, base_form), {})
        return super().get_form(request, obj, **kwargs)

    def get_urls(self):
        """Register breadcrumb redirect URLs for grouper admin views."""
        urls = super().get_urls()

        info = f"{self.content_model._meta.app_label}_{self.content_model._meta.model_name}"
        return [
            path("breadcrumb_redir/<slug>/", self.admin_site.admin_view(self.breadcrumb_redir), name=f"{info}_change"),
            path("breadcrumb_redir/", self.admin_site.admin_view(self.breadcrumb_redir), name=f"{info}_changelist"),
        ] + urls

    def breadcrumb_redir(self, request, *args, **kwargs):
        """Redirect versioning breadcrumb URLs to the grouper admin.

        djangocms-versioning uses content admin URLs for breadcrumbs, but this
        project uses grouper admin classes and must redirect accordingly.
        """
        id = kwargs.get("slug")
        info = f"{self.model._meta.app_label}_{self.model._meta.model_name}"
        if id:
            config = apps.get_app_config("djangocms_custom_content").cms_config
            if self.model in config.cms_toolbar_enabled_models:
                # Redirect to the change view in the toolbar modal
                grouper_model = config.custom_content_groupers[self.model][0]
                info = f"{grouper_model._meta.app_label}_{grouper_model._meta.model_name}"
                return HttpResponseRedirect(admin_reverse(f"{info}_change", args=(id,)))
        return HttpResponseRedirect(admin_reverse(f"{info}_changelist"))
