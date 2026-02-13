from django.apps import apps


def get_custom_config(model):
    """Return the custom content configuration tuple for the given model.

    Looks up the model in the ``custom_content_groupers`` registry and returns
    a tuple of ``(content_model, grouper_field_name, enable_versioning)``.
    If the model is not registered, returns ``(None, None, False)``.
    """
    config = apps.get_app_config("djangocms_custom_content").cms_config
    return config.custom_content_groupers.get(model, (None, None, False))
