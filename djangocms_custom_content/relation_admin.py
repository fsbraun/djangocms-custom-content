"""Admin integration for :mod:`djangocms_custom_content.relations`.

Renders every :class:`~djangocms_custom_content.relations.RelationField` on a
grouper admin as an autocomplete multi-select by default. Ordered relations get
a drag-and-drop sortable variant, mirroring the UX of djangocms-stories'
``SortedManyToManyField`` — but here the field is a generic relation, not a real
M2M, so the autocomplete is served by a small endpoint on the grouper admin
(Django's built-in autocomplete view only resolves real model fields).
"""

from __future__ import annotations

from typing import Protocol

from django import forms
from django.apps import apps
from django.contrib.admin.widgets import AutocompleteSelectMultiple
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import Q, QuerySet
from django.http import HttpRequest, JsonResponse
from django.urls import path, reverse

from djangocms_custom_content.forms import RelationModelForm
from djangocms_custom_content.relations import iter_relation_fields

CONTENT_PREFIX = "content__"


class _RelationTargetAdmin(Protocol):
    search_fields: tuple[str, ...] | list[str]

    def has_view_permission(self, request: HttpRequest) -> bool: ...

    def get_queryset(self, request: HttpRequest) -> QuerySet: ...


# --------------------------------------------------------------------------- #
# Field shim so AutocompleteSelectMultiple can render without a real field
# --------------------------------------------------------------------------- #
class _RemoteShim:
    def __init__(self, model):
        self.model = model


class _FieldShim:
    """Mimics the slice of a relation field the autocomplete widget reads:
    ``.model`` (source), ``.name`` and ``.remote_field.model`` (target)."""

    def __init__(self, model, name, target):
        self.model = model
        self.name = name
        self.remote_field = _RemoteShim(target)


# --------------------------------------------------------------------------- #
# Widgets
# --------------------------------------------------------------------------- #
class RelationAutocompleteSelectMultiple(AutocompleteSelectMultiple):
    """Autocomplete widget pointed at the grouper admin's relation endpoint."""

    def get_url(self):
        opts = self.field.model._meta
        return reverse(f"{self.admin_site.name}:{opts.app_label}_{opts.model_name}_relation_autocomplete")


class SortedRelationAutocompleteSelectMultiple(RelationAutocompleteSelectMultiple):
    """Order-preserving, drag-sortable variant for ``ordered`` relations."""

    def build_attrs(self, base_attrs, extra_attrs=None):
        attrs = super().build_attrs(base_attrs, extra_attrs=extra_attrs)
        attrs["class"] = f"{attrs.get('class', '')} sorted-autocomplete".strip()
        return attrs

    def optgroups(self, name, value, attr=None):
        # The base widget renders selected options in DB order; restore the
        # stored order carried by ``value``.
        groups = super().optgroups(name, value, attr)
        order = {str(v): i for i, v in enumerate(value)}
        for _group_name, subgroup, _index in groups:
            subgroup.sort(key=lambda opt: order.get(str(opt["value"]), len(order)))
        return groups

    @property
    def media(self):
        return super().media + forms.Media(
            js=(
                "djangocms_custom_content/js/Sortable.min.js",
                "djangocms_custom_content/js/sorted-autocomplete.js",
            )
        )


# --------------------------------------------------------------------------- #
# Admin mixin
# --------------------------------------------------------------------------- #
class RelationAdminMixin:
    """Renders the model's relation fields (declared by :class:`RelationModelForm`)
    with autocomplete widgets — sortable when the relation is ordered.

    Field creation, initial values and saving live in
    :class:`~djangocms_custom_content.forms.RelationModelForm`; this mixin only
    ensures that form is in use, swaps in the autocomplete widgets, and serves
    the autocomplete endpoint. Set ``relation_autocomplete = False`` to opt out.
    """

    relation_autocomplete = True

    def _relation_fields(self):
        if not self.relation_autocomplete:
            return {}
        return dict(iter_relation_fields(self.model))

    # -- URLs -------------------------------------------------------------- #
    def get_urls(self):
        urls = super().get_urls()
        if self._relation_fields():
            opts = self.model._meta
            urls = [
                path(
                    "relation-autocomplete/",
                    self.admin_site.admin_view(self.relation_autocomplete_view),
                    name=f"{opts.app_label}_{opts.model_name}_relation_autocomplete",
                )
            ] + urls
        return urls

    def relation_autocomplete_view(self, request):
        empty = JsonResponse({"results": [], "pagination": {"more": False}})
        if not self.has_view_permission(request):
            raise PermissionDenied
        field = self._relation_fields().get(request.GET.get("field_name"))
        if field is None or field.target_model is None:
            return empty
        target = field.target_model
        target_admin = self.admin_site._registry.get(target)
        if target_admin is None or not target_admin.has_view_permission(request):
            return empty
        queryset = self._search_target(target, target_admin, request, request.GET.get("term", ""))
        results = [{"id": str(obj.pk), "text": str(obj)} for obj in queryset[:20]]
        return JsonResponse({"results": results, "pagination": {"more": False}})

    def _search_target(
        self,
        target: type[models.Model],
        target_admin: _RelationTargetAdmin,
        request: HttpRequest,
        term: str,
    ) -> QuerySet:
        """Search the target by its admin ``search_fields``.

        ``GrouperModelAdmin`` declares its search fields with a ``content__``
        prefix; those are routed through the content model's reverse relation
        (e.g. ``content__name`` -> ``personcontent__name``) so the grouper is
        matched by its content. Plain search fields are used as-is.
        """
        queryset = target_admin.get_queryset(request)
        if not term:
            return queryset.distinct()
        content_path = self._content_query_path(target)
        query = Q()
        for search_field in getattr(target_admin, "search_fields", ()) or ():
            path = search_field
            if search_field.startswith(CONTENT_PREFIX):
                if not content_path:
                    continue
                path = f"{content_path}__{search_field[len(CONTENT_PREFIX) :]}"
            query |= Q(**{f"{path}__icontains": term})
        return queryset.filter(query).distinct() if query else queryset.distinct()

    @staticmethod
    def _content_query_path(grouper_model: type[models.Model]) -> str | None:
        """Reverse query name from a grouper to its content model, or ``None``."""
        config = apps.get_app_config("djangocms_custom_content").cms_config
        for content_model, (group_model, group_field, _lang) in config.custom_content_groupers.items():
            if group_model is grouper_model:
                return content_model._meta.get_field(group_field).related_query_name()
        return None

    # -- Form -------------------------------------------------------------- #
    def get_form(self, request, obj=None, **kwargs):
        relation_fields = self._relation_fields()
        if relation_fields:
            # Ensure the form declares + saves the relation fields. Field
            # creation, initial and persistence all live in RelationModelForm.
            base_form = kwargs.get("form", self.form)
            if not (isinstance(base_form, type) and issubclass(base_form, RelationModelForm)):
                base_form = type("RelationModelForm", (RelationModelForm, base_form), {})
            kwargs["form"] = base_form

        form = super().get_form(request, obj, **kwargs)

        if relation_fields:
            self._apply_autocomplete_widgets(form, relation_fields)
        return form

    def _apply_autocomplete_widgets(self, form, relation_fields):
        for name, field in relation_fields.items():
            form_field = form.base_fields.get(name)
            if form_field is None or field.target_model is None:
                continue
            widget_class = (
                SortedRelationAutocompleteSelectMultiple if field.ordered else RelationAutocompleteSelectMultiple
            )
            widget = widget_class(_FieldShim(self.model, name, field.target_model), self.admin_site)
            widget.choices = form_field.choices
            form_field.widget = widget
