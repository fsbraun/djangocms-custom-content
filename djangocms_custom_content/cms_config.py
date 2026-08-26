import logging
from collections.abc import Callable

from cms.app_base import CMSApp, CMSAppConfig, CMSAppExtension
from cms.apphook_pool import apphook_pool
from cms.utils import get_current_site
from cms.utils.i18n import get_language_tuple
from django.apps import apps
from django.contrib.admin import site as admin_site
from django.db import models
from django.urls import path, reverse

from djangocms_custom_content.apphooks import AppHookConfig
from djangocms_custom_content.views import custom_detail_view_factory

logger = logging.getLogger(__name__)


def _get_absolute_url_factory(
    app_name: str,
    slug_field: str,
    view_name: str,
    grouper_field_name: str = "",
    namespace_field: str | None = None,
) -> Callable:
    """Build a ``get_absolute_url`` that reverses into the right app hook instance.

    django CMS registers one URL resolver per app hook *page*, with the page's
    application namespace as the instance namespace. Reversing without
    ``current_app`` therefore always lands on the default instance -- which is
    wrong as soon as the app hook is attached to more than one page.

    ``namespace_field`` names a field on the grouper holding the instance
    namespace an object belongs to. Without it the behaviour is unchanged.
    """

    def _get_absolute_url(self) -> str:
        current_app = None
        if namespace_field and grouper_field_name:
            grouper = getattr(self, grouper_field_name, None)
            current_app = getattr(grouper, namespace_field, None) or None
        return reverse(
            f"{app_name}:{view_name}",
            kwargs={slug_field: getattr(self, slug_field)},
            current_app=current_app,
        )

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
        # Models whose changelist is linked from the admin (site) menu because
        # their content opted in via ``admin_menu = True`` on its ``CMSConfig``.
        # Holds the grouper model for grouper-backed content, or the content
        # model itself for plain (grouper-less) content such as ``FlatCategory``.
        self.admin_menu_models = set()

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

    def register_apphook(self, model: type[models.Model], grouper_model_name: str, grouper_field_name: str = ""):
        """Generate and register the app hook described by ``CMSConfig.apphook``."""
        cms_config = getattr(model, "CMSConfig", None)
        config = AppHookConfig.coerce(getattr(cms_config, "apphook", None))
        if config is None:
            return

        # ``_meta.get_field`` raises rather than returning None, so ask the model.
        route_field = config.slug_field or ("slug" if model.has_slug_field() else "pk")
        route = f"<slug:{route_field}>/" if route_field != "pk" else "<int:pk>/"

        detail_view_class = config.detail_view or custom_detail_view_factory(model)
        detail_view = detail_view_class.as_view()

        # Extra URLs come first so a literal path can win over the slug pattern.
        urls = list(config.extra_urls)
        urls.append(path(route, detail_view, name="detail"))
        if config.list_view is not None:
            # Opt-in only: the app hook root is normally a CMS page carrying the
            # "Custom content list" plugin, which an editor can arrange freely.
            urls.insert(0, path("", config.list_view.as_view(), name="list"))

        app_name = config.app_name or grouper_model_name.lower()
        apphook = type(CMSApp)(
            f"{grouper_model_name}App",
            (CMSApp,),
            {
                "name": config.name or f"{grouper_model_name}",
                "app_name": app_name,
                "get_urls": lambda self, page=None, language=None, **kwargs: list(urls),
            },
        )
        apphook_pool.register(apphook)

        if not hasattr(model, "get_absolute_url"):
            model.add_to_class(
                "get_absolute_url",
                _get_absolute_url_factory(
                    app_name,
                    route_field,
                    "detail",
                    grouper_field_name=grouper_field_name,
                    namespace_field=config.namespace_field,
                ),
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

        # Opt into an admin (site) menu shortcut. Grouper-backed content links
        # to the grouper changelist; a plain (grouper-less) content model such
        # as ``FlatCategory`` links to its own changelist.
        cms_config = getattr(model, "CMSConfig", None)
        if getattr(cms_config, "admin_menu", False):
            self.admin_menu_models.add(grouper_model or model)

        self.register_frontend_editing(model, grouper_field_name)
        self.register_versioning(model, grouper_field_name, has_language_field)
        if grouper_field_name:
            self.register_apphook(model, grouper_model.__name__, grouper_field_name)
        else:
            self.register_apphook(model, model.__name__)


class CustomContentExtension(CMSAppExtension):
    # Allow extension of apps that set djangocms_custom_content_enabled = True
    # No contract object needed.
    contract = "djangocms_custom_content", None

    def configure_app(self, cms_config):
        pass
