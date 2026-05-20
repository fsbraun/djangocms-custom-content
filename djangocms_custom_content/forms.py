"""Form field and widget for CMSConfig.m2m relations in the admin."""

from django import forms
from django.contrib.admin.widgets import AutocompleteSelectMultiple, get_select2_language
from django.urls import reverse


class _M2MTargetShim:
    """Minimal stand-in for a Django field, used by AutocompleteMixin.

    The stock ``AutocompleteSelectMultiple`` expects a real model ForeignKey/
    ManyToManyField so it can pull ``data-app-label`` / ``data-model-name`` /
    ``data-field-name`` from it. Our virtual m2m doesn't have one, so we
    expose just the attributes the mixin reads.
    """

    def __init__(self, target_model):
        self.name = ""
        self.model = target_model

        class _RemoteShim:
            model = target_model
            field_name = target_model._meta.pk.attname

        self.remote_field = _RemoteShim()


class M2MAutocompleteSelectMultiple(AutocompleteSelectMultiple):
    """Autocomplete multi-select backed by a target model (no source db_field).

    Differs from the stock widget in two ways:

    * It's parameterised by ``target_model`` directly (no Django field), so it
      can back a virtual m2m relation declared via ``CMSConfig.m2m``.
    * It points at the framework's own autocomplete endpoint, so the URL
      doesn't need a source ModelAdmin with a real m2m field on it.

    This widget is **not** sortable. Use :class:`SortedAutocompleteSelectMultiple`
    when drag-to-reorder is wanted.
    """

    url_name = "%%s:%s" % "djangocms_custom_content_m2m_autocomplete"

    def __init__(self, target_model, admin_site, attrs=None, choices=(), using=None):
        self.target_model = target_model
        self.field = _M2MTargetShim(target_model)
        self.admin_site = admin_site
        self.db = using
        self.choices = choices
        self.attrs = {} if attrs is None else attrs.copy()
        self.i18n_name = get_select2_language()

    def get_url(self):
        return reverse(self.url_name % self.admin_site.name)


class SortedAutocompleteSelectMultiple(M2MAutocompleteSelectMultiple):
    """Autocomplete multi-select that preserves selected-value order and ships
    Sortable.js + an initialiser so users can drag chips to reorder."""

    def build_attrs(self, base_attrs, extra_attrs=None):
        attrs = super().build_attrs(base_attrs, extra_attrs=extra_attrs)
        attrs["class"] = (
            attrs.get("class", "") + " djangocms-custom-content-m2m-sortable"
        ).strip()
        return attrs

    def optgroups(self, name, value, attr=None):
        groups = super().optgroups(name, value, attr)
        order = {str(v): i for i, v in enumerate(value)}
        for _group_name, subgroup, _idx in groups:
            subgroup.sort(key=lambda opt: order.get(str(opt["value"]), len(order)))
        return groups

    @property
    def media(self):
        return super().media + forms.Media(
            js=(
                "djangocms_custom_content/js/Sortable.min.js",
                "djangocms_custom_content/js/m2m-sortable.js",
            ),
        )


class CustomM2MField(forms.ModelMultipleChoiceField):
    """ModelMultipleChoiceField backed by a ``CMSConfig.m2m`` accessor.

    By default renders as a non-sortable autocomplete multi-select. Pass
    ``sortable=True`` to swap in :class:`SortedAutocompleteSelectMultiple`
    (and have ``clean()`` return values in the submitted order so the
    persisted order matches the UI).
    """

    def __init__(self, target_model, admin_site, sortable=False, **kwargs):
        self.sortable = sortable
        widget_class = SortedAutocompleteSelectMultiple if sortable else M2MAutocompleteSelectMultiple
        kwargs.setdefault("queryset", target_model._default_manager.all())
        kwargs.setdefault("required", False)
        kwargs.setdefault(
            "widget", widget_class(target_model, admin_site, attrs=kwargs.pop("attrs", None))
        )
        super().__init__(**kwargs)

    def clean(self, value):
        qs = super().clean(value)
        if not value:
            return []
        if not self.sortable:
            return list(qs)
        # For sortable relations, re-order to match the submitted sequence so
        # callers can pass the result straight to ``manager.set(...)``.
        objs_by_pk = {str(obj.pk): obj for obj in qs}
        return [objs_by_pk[str(v)] for v in value if str(v) in objs_by_pk]
