"""Tests for :class:`~djangocms_custom_content.apphooks.AppHookConfig`."""

import pytest
from cms.apphook_pool import apphook_pool
from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import path
from django.views.generic import TemplateView

from djangocms_custom_content.apphooks import AppHookConfig
from djangocms_custom_content.contrib.people.models import Person, PersonContent
from tests.test_app.models import SampleGrouperContent

User = get_user_model()
pytestmark = pytest.mark.django_db


class AppHookConfigTests(TestCase):
    """``CMSConfig.apphook`` accepts a boolean or a config; both mean the same thing."""

    def test_true_becomes_a_default_config(self):
        config = AppHookConfig.coerce(True)

        self.assertIsInstance(config, AppHookConfig)
        self.assertIsNone(config.detail_view)
        self.assertIsNone(config.namespace_field)

    def test_no_list_view_by_default(self):
        """The app hook root is a CMS page carrying the list plugin, not a view."""
        self.assertIsNone(AppHookConfig().list_view)

    def test_falsy_means_no_apphook(self):
        self.assertIsNone(AppHookConfig.coerce(False))
        self.assertIsNone(AppHookConfig.coerce(None))

    def test_a_config_is_returned_unchanged(self):
        config = AppHookConfig(app_name="people")

        self.assertIs(AppHookConfig.coerce(config), config)


class GeneratedUrlTests(TestCase):
    """What ``register_apphook`` puts in ``get_urls()``."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser("admin", "admin@example.com", "pw")

    def setUp(self):
        self.cms_config = django_apps.get_app_config("djangocms_custom_content").cms_config
        self.registered = []
        self.added_urls_to = []

    def tearDown(self):
        for name in self.registered:
            apphook_pool.apps.pop(name, None)
        # ``register_apphook`` adds ``get_absolute_url`` to models that lack one.
        # That outlives the test unless it is taken off again.
        for model in self.added_urls_to:
            del model.get_absolute_url

    def register(self, model, grouper_name, config, grouper_field=""):
        had_absolute_url = "get_absolute_url" in model.__dict__
        model.CMSConfig = type("CMSConfig", (), {"apphook": config})
        try:
            self.cms_config.register_apphook(model, grouper_name, grouper_field)
        finally:
            del model.CMSConfig
        if not had_absolute_url and "get_absolute_url" in model.__dict__:
            self.added_urls_to.append(model)
        name = f"{grouper_name}App"
        self.registered.append(name)
        return apphook_pool.apps[name]

    def routes(self, apphook):
        return [(pattern.pattern._route, pattern.name) for pattern in apphook.get_urls()]

    def test_slug_route_when_the_model_has_a_slug(self):
        apphook = self.register(PersonContent, "SlugRouted", AppHookConfig(), "person")

        self.assertIn(("<slug:slug>/", "detail"), self.routes(apphook))

    def test_pk_route_when_the_model_has_no_slug(self):
        """``_meta.get_field`` raises rather than returning None, so this branch
        used to be unreachable and a slugless model crashed at startup."""
        apphook = self.register(SampleGrouperContent, "PkRouted", AppHookConfig(), "grouper")

        self.assertIn(("<int:pk>/", "detail"), self.routes(apphook))

    def test_extra_urls_precede_the_detail_route(self):
        extra = path("archive/", TemplateView.as_view(template_name="x.html"), name="archive")

        apphook = self.register(PersonContent, "WithExtras", AppHookConfig(extra_urls=[extra]), "person")

        routes = self.routes(apphook)
        self.assertEqual(routes[0], ("archive/", "archive"))
        self.assertLess(routes.index(("archive/", "archive")), routes.index(("<slug:slug>/", "detail")))

    def test_list_view_is_opt_in_and_takes_the_root(self):
        config = AppHookConfig(list_view=TemplateView)

        apphook = self.register(PersonContent, "WithList", config, "person")

        routes = self.routes(apphook)
        self.assertEqual(routes[0], ("", "list"))

    def test_no_list_route_without_a_list_view(self):
        apphook = self.register(PersonContent, "NoList", AppHookConfig(), "person")

        self.assertNotIn("list", [name for _route, name in self.routes(apphook)])

    def test_a_custom_slug_field_routes_and_resolves(self):
        """The URL parameter is named after the field, so the view must be told
        about it -- otherwise it looks for ``slug``/``pk`` and finds neither."""
        apphook = self.register(PersonContent, "FieldRouted", AppHookConfig(slug_field="name"), "person")

        self.assertIn(("<slug:name>/", "detail"), self.routes(apphook))

        view = apphook.get_urls()[0].callback
        self.assertEqual(view.view_initkwargs, {"slug_field": "name", "slug_url_kwarg": "name"})

    def test_a_custom_slug_field_finds_the_object(self):
        from djangocms_versioning.constants import DRAFT
        from djangocms_versioning.models import Version

        person = Person.objects.create()
        PersonContent.objects.with_user(self.user).create(
            person=person, slug="ada-lovelace", name="Ada", role="", description=""
        )
        for version in Version.objects.filter_by_grouper(person).filter(state=DRAFT):
            version.publish(self.user)
        apphook = self.register(PersonContent, "FieldLookup", AppHookConfig(slug_field="name"), "person")

        view = apphook.get_urls()[0].callback
        instance = view.view_class(**view.view_initkwargs)
        instance.kwargs = {"name": "Ada"}
        instance.request = None

        self.assertEqual(instance.get_object().name, "Ada")

    def test_the_default_route_passes_no_view_kwargs(self):
        apphook = self.register(PersonContent, "PlainSlug", AppHookConfig(), "person")

        self.assertEqual(apphook.get_urls()[0].callback.view_initkwargs, {})

    def test_registration_does_not_leak_get_absolute_url(self):
        """``register_apphook`` mutates the model class; the helper must undo it."""
        self.assertNotIn("get_absolute_url", SampleGrouperContent.__dict__)

        self.register(SampleGrouperContent, "LeakCheck", AppHookConfig(), "grouper")
        self.assertIn("get_absolute_url", SampleGrouperContent.__dict__)

        self.tearDown()
        self.registered, self.added_urls_to = [], []
        self.assertNotIn("get_absolute_url", SampleGrouperContent.__dict__)

    def test_app_name_can_be_overridden(self):
        apphook = self.register(PersonContent, "Renamed", AppHookConfig(app_name="staff"), "person")

        self.assertEqual(apphook.app_name, "staff")
