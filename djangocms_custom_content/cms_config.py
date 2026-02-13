from collections.abc import Callable

from cms.app_base import CMSApp, CMSAppConfig
from cms.apphook_pool import apphook_pool
from cms.utils import get_current_site
from cms.utils.i18n import get_language_tuple
from django.apps import apps
from django.contrib.admin import site as admin_site
from django.core.exceptions import FieldDoesNotExist, ImproperlyConfigured
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
            has_slug_field = model._meta.get_field("slug") is not None

            apphook = type(CMSApp)(
                f"{grouper_model_name}App",
                (CMSApp,),
                {
                    "name": f"{grouper_model_name}",
                    "app_name": grouper_model_name.lower(),
                    "get_urls": lambda self, page=None, language=None, **kwargs: [
                        path("<slug:slug>/" if has_slug_field else "<int:pk>/", detail_view, name="detail"),
                    ],
                },
            )
            apphook_pool.register(apphook)

            if not hasattr(model, "get_absolute_url"):
                model.add_to_class(
                    "get_absolute_url",
                    _get_absolute_url_factory(
                        grouper_model_name.lower(), "slug" if has_slug_field else "pk", "detail"
                    ),
                )

    @staticmethod
    def is_relation_for(model: type[models.Model]):
        from djangocms_custom_content.models import AbstractCustomRelation

        try:
            if issubclass(model, AbstractCustomRelation):
                print(model.__name__, model._meta.get_field("instance").related_model)
                return model._meta.get_field("instance").related_model
        except FieldDoesNotExist:
            pass
        return None

    def register_m2m_relation(self, model: type[models.Model]):
        """
        Register many-to-many relations defined in the model's CMSConfig.

        This method processes the ``m2m_relations`` attribute from a model's CMSConfig
        and sets up reverse accessors on the target models. Each relation defined as:

            m2m_relations = [("accessor_name", "app_label.ModelName")]

        Will add an ``accessor_name`` property to the target model that returns a
        GenericM2MManager for managing the relationship.

        The target model will be able to access linked objects via:
            target_instance.accessor_name.all()
            target_instance.accessor_name.add(obj)
            target_instance.accessor_name.remove(obj)
            target_instance.accessor_name.clear()

        Args:
            model: The content model to register m2m relations for

        Raises:
            ImproperlyConfigured: If m2m_relations is defined but the relation model
                                  (created via custom_relation_factory) is not found
        """
        from djangocms_custom_content.models import GenericM2MDescriptor

        cms_config = getattr(model, "CMSConfig", None)
        m2m_relations = getattr(cms_config, "m2m_relations", [])
        if m2m_relations:
            relation_model = next(
                (_model for _model in apps.get_models() if self.is_relation_for(_model) is model), None
            )
            if not relation_model:
                raise ImproperlyConfigured(
                    f"Use {model.__name__}Relation = custom_relation_factory({model.__name__}) in your models.py to create a "
                    "m2m relation model allowing for CMSConfig.m2m_relations"
                )
            for reverse_name, relation in m2m_relations:
                try:
                    related_model = apps.get_model(relation)
                    related_model.add_to_class(reverse_name, GenericM2MDescriptor(relation_model, "instance"))
                except LookupError:
                    # Related model not installed, skip registration
                    pass

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
        self.register_m2m_relation(model)
