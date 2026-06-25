from cms.utils.urlutils import admin_reverse
from django.apps import apps
from django.http import HttpResponseRedirect
from django.urls import path

from djangocms_custom_content.relation_admin import RelationAdminMixin


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
