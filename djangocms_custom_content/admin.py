from cms.utils.urlutils import admin_reverse
from django.apps import apps
from django.db import models
from django.db.models import Prefetch
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import path

from djangocms_custom_content.views import CustomM2MAutocompleteView


M2M_AUTOCOMPLETE_URL_NAME = "djangocms_custom_content_m2m_autocomplete"


def register_m2m_autocomplete_url(admin_site):
    """Install the m2m autocomplete view on ``admin_site``.

    Wraps ``admin_site.get_urls`` so the same endpoint is exposed on whichever
    ``AdminSite`` instance is in use (default ``admin.site`` by default, but
    projects may register their own).
    """
    if getattr(admin_site, "_djangocms_custom_content_m2m_url_registered", False):
        return
    admin_site._djangocms_custom_content_m2m_url_registered = True

    original_get_urls = admin_site.get_urls

    def get_urls():
        urls = original_get_urls()
        extra = [
            path(
                "djangocms_custom_content/m2m-autocomplete/",
                admin_site.admin_view(CustomM2MAutocompleteView.as_view()),
                name=M2M_AUTOCOMPLETE_URL_NAME,
            ),
        ]
        return extra + urls

    admin_site.get_urls = get_urls


class CustomGrouperAdminMixin:
    """Admin mixin to optimize queries and redirect content endpoints.

    This mixin prefetches related content for admin lists and provides a
    breadcrumb redirect compatible with django CMS versioning.
    """

    def get_queryset(self, request: HttpRequest):
        """Return a queryset prefetched with latest related content.

        Args:
            ``request``: The current admin request.

        Returns:
            The queryset, optionally prefetched with admin manager content.
        """
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
        prefetch = Prefetch(accessor_name, queryset=manager.latest_content(), to_attr="_admin_prefetch_cache")

        return qs.prefetch_related(prefetch)

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


class _CustomM2MFormMixin:
    """Mixin baked onto admin forms to populate m2m initial values from the instance."""

    _custom_m2m_field_names: list[str] = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = getattr(self, "instance", None)
        if instance is not None and instance.pk:
            for name in self._custom_m2m_field_names:
                if name in self.fields:
                    self.fields[name].initial = list(getattr(instance, name).all())


class CustomM2MAdminMixin:
    """Surface ``CMSConfig.m2m`` accessors as autocomplete fields in admin.

    Two opt-in lists:

    * ``m2m_fields`` — plain autocomplete multi-select (no drag-to-reorder).
    * ``m2m_sortable_fields`` — autocomplete + Sortable.js drag-to-reorder;
      the chosen order is persisted in the through-table's ``order`` column.

    A field name may appear in only one of the two lists. Example::

        class BlogPostAdmin(CustomM2MAdminMixin, GrouperModelAdmin):
            m2m_fields = ["categories"]
            m2m_sortable_fields = ["authors"]

    For each declared accessor the mixin:

    * Locates the matching ``CMSConfig.m2m`` descriptor on ``self.model``.
    * Declares a ``CustomM2MField`` on the admin form class so Django's
      ``modelform_factory`` accepts the field name in its ``fields`` list.
    * Populates the field's initial value from the saved relations on form
      instantiation (in persisted order for sortable fields).
    * On save, calls ``instance.<accessor>.set(values)`` so the chosen order
      is persisted in the through-table's ``order`` column.

    The target model must be registered with the admin site and define
    ``search_fields`` for the autocomplete endpoint to return results.
    """

    m2m_fields: list[str] = []
    m2m_sortable_fields: list[str] = []

    def _custom_m2m_descriptors(self):
        """Return ``{accessor_name: (target_model, sortable)}`` for declared accessors."""
        from djangocms_custom_content.models import _CustomM2MDescriptor

        result = {}
        for name in self.m2m_fields:
            descriptor = getattr(self.model, name, None)
            if isinstance(descriptor, _CustomM2MDescriptor):
                result[name] = (descriptor.target_model, False)
        for name in self.m2m_sortable_fields:
            descriptor = getattr(self.model, name, None)
            if isinstance(descriptor, _CustomM2MDescriptor):
                result[name] = (descriptor.target_model, True)
        return result

    def get_form(self, request, obj=None, change=False, **kwargs):
        from django import forms as django_forms

        from djangocms_custom_content.forms import CustomM2MField

        descriptors = self._custom_m2m_descriptors()
        if descriptors:
            admin_site = self.admin_site
            extras = {
                name: CustomM2MField(
                    target_model=target_model,
                    admin_site=admin_site,
                    sortable=sortable,
                    label=name.replace("_", " ").capitalize(),
                )
                for name, (target_model, sortable) in descriptors.items()
            }
            base_form = kwargs.pop("form", None) or getattr(self, "form", django_forms.ModelForm)
            form_with_extras = type(
                base_form.__name__,
                (_CustomM2MFormMixin, base_form),
                {
                    **extras,
                    "_custom_m2m_field_names": list(descriptors.keys()),
                },
            )
            kwargs["form"] = form_with_extras

        return super().get_form(request, obj=obj, change=change, **kwargs)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        for name in self._custom_m2m_descriptors():
            if name in form.cleaned_data:
                getattr(obj, name).set(form.cleaned_data[name])
