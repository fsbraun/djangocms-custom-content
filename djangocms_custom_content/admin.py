from cms.utils.urlutils import admin_reverse
from django.apps import apps
from django.db import models
from django.db.models import Prefetch
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import path


class CustomGrouperAdminMixin:
    def get_queryset(self, request: HttpRequest):
        """Override the default queryset to only show groupers that have content."""
        qs = super().get_queryset(request)
        content_model = getattr(self, "content_model", None)
        if content_model is None:
            return qs

        grouper_fk_field = next(
            (
                f
                for f in content_model._meta.get_fields()
                if isinstance(f, models.ForeignKey) and f.related_model is self.model
            ),
            None,
        )
        if grouper_fk_field is None:
            return qs
        accessor_name = grouper_fk_field.remote_field.get_accessor_name()
        manager = content_model._meta.managers_map.get("admin_manager", content_model._default_manager)
        prefetch = Prefetch(accessor_name, queryset=manager.latest_content(), to_attr="_content_prefetch_cache")

        return qs.prefetch_related(prefetch)

    def get_urls(self):
        urls = super().get_urls()

        info = f"{self.content_model._meta.app_label}_{self.content_model._meta.model_name}"
        return [
            path("breadcrumb_redir/<slug>/", self.admin_site.admin_view(self.breadcrumb_redir), name=f"{info}_change"),
            path("breadcrumb_redir/", self.admin_site.admin_view(self.breadcrumb_redir), name=f"{info}_changelist"),
        ] + urls

    def breadcrumb_redir(self, request, *args, **kwargs):
        """djangocms-versioning uses content admin urls for breadcrumbs, but
        we use grouper admin classes and want to redirect to the grouper 
        admin urls instead."""
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
