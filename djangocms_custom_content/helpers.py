from django.apps import apps
from django.db import models


def get_custom_config(model):
    """Return the custom content configuration tuple for the given model.

    Looks up the model in the ``custom_content_groupers`` registry and returns
    a tuple of ``(content_model, grouper_field_name, enable_versioning)``.
    If the model is not registered, returns ``(None, None, False)``.
    """
    app_config = apps.get_app_config("djangocms_custom_content")
    cms_config = getattr(app_config, "cms_config", None)
    if cms_config is not None:
        registered = cms_config.custom_content_groupers.get(model)
        if registered is not None:
            return registered

    # django CMS has not run its config (or is not installed), so derive the
    # same information directly from the model.
    from djangocms_custom_content.models import CustomGrouperMixin

    grouper_field = next(
        (
            field
            for field in model._meta.get_fields()
            if isinstance(field, models.ForeignKey) and issubclass(field.related_model, CustomGrouperMixin)
        ),
        None,
    )
    if grouper_field is None:
        return (None, None, False)
    return (
        grouper_field.related_model,
        grouper_field.name,
        any(field.name == "language" for field in model._meta.get_fields()),
    )
