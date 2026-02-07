from django.apps import apps


def get_custom_config(model):
    config = apps.get_app_config("djangocms_custom_content").cms_config
    return config.custom_content_groupers.get(model, (None, None, False))
