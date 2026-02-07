from typing import Callable
from cms.app_base import CMSApp, CMSAppConfig
from cms.apphook_pool import apphook_pool
from cms.utils import get_current_site
from cms.utils.i18n import get_language_tuple
from django.apps import apps
from django.contrib.admin import site as admin_site
from django.db import models
from django.urls import path, reverse

from djangocms_custom_content.views import custom_detail_view_factory


def _get_absolute_url_factory(app_name: str, slug_field: str, view_name: str) -> Callable:
    def _get_absolute_url(self) -> str:
        return reverse(f"{app_name}:{view_name}", kwargs={slug_field: getattr(self, slug_field)})
    return _get_absolute_url


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
        
    def register_extra_grouping_field(self, grouper_model: type[models.Model]):
        # Add extra_grouping_field to admin

        admin = admin_site._registry.get(grouper_model)
        if admin:
            admin.__class__.extra_grouping_fields = ("language",)

    def register_frontend_editing(self, model: type[models.Model], grouper_field_name: str):
        from djangocms_custom_content.views import render_frontend_editor

        cms_config = getattr(model, "CMSConfig", None)
        enable_frontend_editing = getattr(cms_config, "enable_frontend_editing", False)
        if enable_frontend_editing:
            # Add frontend editable models
            self.cms_toolbar_enabled_models.append((model, render_frontend_editor, grouper_field_name))

    def register_versioning(self, model: type[models.Model], grouper_field_name: str, has_language_field: bool):
        cms_config = getattr(model, "CMSConfig", None)
        enable_versioning = getattr(cms_config, "enable_versioning", False)
        if enable_versioning and getattr(self, "versioning_contract", None):
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

    def register_apphook(self, model: type[models.Model], grouper_model_name: str):
        cms_config = getattr(model, "CMSConfig", None)
        apphook = getattr(cms_config, "apphook", None)
        if apphook:
            
            detail_view = custom_detail_view_factory(model).as_view()

            apphook = type(CMSApp)(
                f"{grouper_model_name}App",
                (CMSApp,),
                {
                    "name": f"{grouper_model_name}",
                    "app_name": grouper_model_name.lower(),
                    "get_urls": lambda self, page=None, language=None, **kwargs: [
                        path("<slug:slug>/", detail_view, name="detail"),
                    ],
                },
            )
            apphook_pool.register(apphook)

            if not hasattr(model, "get_absolute_url"):
                model.add_to_class("get_absolute_url", _get_absolute_url_factory(grouper_model_name.lower(), "slug", "detail"))


    def register(self, model: type[models.Model]):
        from djangocms_custom_content.models import AbstractCustomGrouper
    
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

        if has_language_field and grouper_model is not None:
            self.register_extra_grouping_field(grouper_model)

        self.register_frontend_editing(model, grouper_field_name)
        self.register_versioning(model, grouper_field_name, has_language_field)
        self.register_apphook(model, grouper_model.__name__)
 