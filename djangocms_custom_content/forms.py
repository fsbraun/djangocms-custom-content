"""Form-layer support for :mod:`djangocms_custom_content.relations`.

:class:`RelationModelForm` makes every forward ``RelationField`` on a model
behave like a real relation on *any* ``ModelForm`` — not just in the admin:

- the fields are declared at class level (via the metaclass), so they render and
  validate like ordinary form fields;
- initial values are loaded from the relation manager;
- selections are persisted in ``_save_m2m`` (exactly where Django saves real
  many-to-many data), so ``form.save()`` "just works".

The admin layer only swaps in the autocomplete widgets; the field lifecycle
lives here.
"""

from __future__ import annotations

from typing import Any

from django import forms
from django.forms.models import ModelFormMetaclass

from djangocms_custom_content.relations import iter_relation_fields


class OrderedModelMultipleChoiceField(forms.ModelMultipleChoiceField):
    """Like ``ModelMultipleChoiceField`` but returns objects in submitted order.

    A sortable widget reorders the ``<option>`` elements, so the browser submits
    the pks in the user's chosen order; the default field would re-sort them by
    the database. This preserves the drag order for ordered relations.
    """

    def clean(self, value):
        result = super().clean(value)
        order = {str(v): i for i, v in enumerate(value or [])}
        return sorted(result, key=lambda obj: order.get(str(obj.pk), len(order)))


def build_relation_formfield(relation_field, *, widget=None, label=None):
    """Build a (multiple) choice field for a :class:`RelationField`.

    Ordered relations get the order-preserving field. The widget is left to the
    caller (the admin supplies an autocomplete widget); by default Django's
    plain multi-select is used, so the field is usable in any form.
    """
    target = relation_field.target_model
    field_class = OrderedModelMultipleChoiceField if relation_field.ordered else forms.ModelMultipleChoiceField
    return field_class(
        queryset=target._default_manager.all(),
        required=False,
        widget=widget,
        label=label or relation_field.name.replace("_", " ").capitalize(),
    )


class RelationModelFormMetaclass(ModelFormMetaclass):
    """Declares a form field for each forward ``RelationField`` on the model.

    Fields are injected into ``attrs`` *before* the base metaclass runs so they
    count as declared fields — otherwise ``modelform_factory``'s ``fields``
    validation would reject them as unknown.
    """

    def __new__(mcs, name, bases, attrs):
        model = getattr(attrs.get("Meta"), "model", None)
        if model is None:
            for base in bases:
                model = getattr(getattr(base, "_meta", None), "model", None)
                if model is not None:
                    break
        if model is not None:
            for field_name, relation_field in iter_relation_fields(model):
                if relation_field.target_model is not None and field_name not in attrs:
                    attrs[field_name] = build_relation_formfield(relation_field)
        return super().__new__(mcs, name, bases, attrs)


class RelationModelForm(forms.ModelForm, metaclass=RelationModelFormMetaclass):
    """``ModelForm`` that exposes a model's grouper relations as form fields."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        instance = getattr(self, "instance", None)
        if instance is not None and instance.pk:
            for field_name, _relation_field in iter_relation_fields(self._meta.model):
                if field_name in self.fields:
                    self.initial.setdefault(
                        field_name,
                        list(getattr(instance, field_name).all().values_list("pk", flat=True)),
                    )

    def _save_m2m(self) -> None:
        super()._save_m2m()
        for field_name, relation_field in iter_relation_fields(self._meta.model):
            if field_name in self.cleaned_data:
                submitted = [obj.pk for obj in self.cleaned_data[field_name]]
                current = list(getattr(self.instance, field_name).all().values_list("pk", flat=True))
                relation_changed = current != submitted if relation_field.ordered else set(current) != set(submitted)
                if relation_changed:
                    getattr(self.instance, field_name).set(self.cleaned_data[field_name])
