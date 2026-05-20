from collections.abc import Callable

from cms.app_base import CMSApp, CMSAppConfig, CMSAppExtension
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
    djangocms_custom_content_enabled = True

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
            if grouper_field_name:
                self.cms_toolbar_enabled_models.append((model, render_frontend_editor, grouper_field_name))
            else:
                self.cms_toolbar_enabled_models.append((model, render_frontend_editor))

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

    def register_m2m(self, model: type[models.Model], owner_cls: type[models.Model]):
        """Register ``CMSConfig.m2m`` declarations.

        For each entry the framework installs a forward accessor on ``owner_cls``
        (the grouper if the content has one, otherwise the content model itself)
        and a reverse accessor on the target model.

        2-tuples ``(forward, target)`` auto-derive the reverse name as
        ``"{owner_lowercase}_set"``. 3-tuples ``(forward, target, reverse)``
        pass an explicit reverse name; pass ``None`` to suppress the reverse
        accessor entirely.

        If the target model is not installed the forward accessor is wired to
        a dummy manager so attribute access keeps working without raising.
        """
        from djangocms_custom_content.models import (
            _AUTO_REVERSE,
            FK_SIDE,
            GFK_SIDE,
            _CustomM2MDescriptor,
            _DummyM2MDescriptor,
            _normalize_m2m_decl,
            _through_model_name,
        )

        cms_config = getattr(model, "CMSConfig", None)
        m2m_decls = getattr(cms_config, "m2m", None) if cms_config else None
        if not m2m_decls:
            return

        through_model = apps.get_model(model._meta.app_label, _through_model_name(model))
        auto_reverse_name = f"{owner_cls._meta.model_name}_set"

        for decl in m2m_decls:
            forward_name, target_label, reverse_name = _normalize_m2m_decl(decl)
            if reverse_name is _AUTO_REVERSE:
                reverse_name = auto_reverse_name
            try:
                target_cls = apps.get_model(target_label)
            except (LookupError, ValueError):
                # LookupError: target app or model is not installed.
                # ValueError: target_label is malformed (e.g. missing or extra
                # dots). In both cases we fall back to a dummy descriptor so
                # the m2m relation is effectively ignored and the rest of the
                # framework keeps working.
                owner_cls.add_to_class(forward_name, _DummyM2MDescriptor())
                continue

            owner_cls.add_to_class(
                forward_name,
                _CustomM2MDescriptor(through_model, target_cls, side=FK_SIDE, relation_name=forward_name),
            )
            if reverse_name:
                target_cls.add_to_class(
                    reverse_name,
                    _CustomM2MDescriptor(through_model, owner_cls, side=GFK_SIDE, relation_name=forward_name),
                )

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
        has_language_field = False
        grouper_model = None
        if grouper_field_name:
            grouper_model = model._meta.get_field(grouper_field_name).related_model
            has_language_field = any(f.name == "language" for f in model._meta.get_fields())

            self.custom_content_groupers[model] = (grouper_model, grouper_field_name, has_language_field)

            if has_language_field and grouper_model is not None:
                self.register_extra_grouping_field(grouper_model)

        self.register_frontend_editing(model, grouper_field_name)
        self.register_versioning(model, grouper_field_name, has_language_field)
        if grouper_field_name:
            self.register_apphook(model, grouper_model.__name__)
        else:
            self.register_apphook(model, model.__name__)
        self.register_m2m(model, grouper_model or model)


class CustomContentExtension(CMSAppExtension):
    # Allow extension of apps that set djangocms_custom_content_enabled = True
    # No contract object needed.
    contract = "djangocms_custom_content", None

    def configure_app(self, cms_config):
        # Custom-content app extensions no longer carry any m2m metadata —
        # m2m wiring happens entirely via CMSConfig.m2m on the content model.
        return
