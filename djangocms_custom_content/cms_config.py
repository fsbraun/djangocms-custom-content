from cms.app_base import CMSAppConfig
from cms.utils import get_current_site
from cms.utils.i18n import get_language_tuple
from django.apps import apps
from django.contrib.admin import site as admin_site
from django.db import models


class CustomContentConfig(CMSAppConfig):
    cms_enabled = True
    djangocms_versioning_enabled = True

    def __init__(self, args, **wkargs):
        from djangocms_custom_content.models import AbstractCustomContent

        super().__init__(args, **wkargs)
        # Ensure admins are loaded
        admin_config = apps.get_app_config("admin")
        if admin_config.module:
            admin_config.module.autodiscover()

        self.init_config()
        all_models = apps.get_models()
        for model in all_models:
            if not model._meta.abstract and issubclass(model, AbstractCustomContent):
                self.register(model)

    def init_config(self) -> None:
        self.cms_toolbar_enabled_models = []
        self.cms_apphook_dict = {}
        self.custom_content_groupers = {}

        if hasattr(self, "get_contract"):
            self.versioning_contract = self.get_contract("djangocms_versioning")
            self.versioning = []
        else:
            try:
                from djangocms_versioning.datastructures import VersionableItem

                self.versioning_contract = VersionableItem
                self.versioning = []
            except ImportError:
                pass

    def register(self, model: type[models.Model]):
        from djangocms_custom_content.models import AbstractCustomGrouper
        from djangocms_custom_content.views import render_frontend_editor

        cms_config = getattr(model, "CMSConfig", None)
        enable_versionig = getattr(cms_config, "enable_versioning", False)
        enable_frontend_editing = getattr(cms_config, "enable_frontend_editing", False)

        grouper_field_name = next(
            (
                f.name
                for f in model._meta.get_fields()
                if isinstance(f, models.ForeignKey) and issubclass(f.related_model, AbstractCustomGrouper)
            ),
            "",
        )
        grouper_model = model._meta.get_field(grouper_field_name).related_model
        has_language_field = any(f.name == "language" for f in model._meta.get_fields())

        self.custom_content_groupers[model] = (grouper_model, grouper_field_name, has_language_field)

        if has_language_field:
            # Add extra_grouping_field to admin

            admin = admin_site._registry.get(grouper_model)
            if admin:
                admin.__class__.extra_grouping_fields = ("language",)

        if enable_frontend_editing:
            # Add frontend editable models
            self.cms_toolbar_enabled_models.append((model, render_frontend_editor, grouper_field_name))

        if enable_versionig and hasattr(self, "versioning_contract"):
            # Add versioning enabled models
            self.versioning.append(
                self.versioning_contract(
                    content_model=model,
                    grouper_field_name=grouper_field_name,
                    extra_grouping_fields=["language"] if has_language_field else [],
                    version_list_filter_lookups={
                        "language": lambda *args: get_language_tuple(
                            site_id=get_current_site(args[0] if len(args) > 0 else None).pk
                        )
                    }
                    if has_language_field
                    else {},
                    grouper_admin_mixin="__default__",
                )
            )
