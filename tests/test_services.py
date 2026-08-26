"""Tests for the Services example contrib app.

Covers the ``Service``/``ServiceContent`` grouper pair and the two plugins'
``render()`` logic. The render methods are exercised directly (with unsaved plugin
instances and a plain context dict) rather than via full template rendering, so the
context-building branches are tested without depending on project templates.
"""

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import TestCase

from djangocms_custom_content.contrib.services.cms_plugins import (
    FeaturedServicesPlugin,
    ServiceTeaserPlugin,
)
from djangocms_custom_content.contrib.services.models import (
    FeaturedServices,
    Service,
    ServiceContent,
    ServiceTeaser,
)

User = get_user_model()
pytestmark = pytest.mark.django_db


class ServicesTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser("admin", "admin@example.com", "pw")

    def create_service(self, title, slug, is_featured=False, summary=""):
        """Create a grouper with one (published) content object and return the grouper."""
        service = Service.objects.create()
        ServiceContent.objects.with_user(self.user).create(
            service=service, title=title, slug=slug, summary=summary, is_featured=is_featured
        )
        self.publish(service)
        return service

    def publish(self, service):
        from djangocms_versioning.constants import DRAFT
        from djangocms_versioning.models import Version

        version = Version.objects.filter_by_grouper(service).filter(state=DRAFT).first()
        if version is not None:
            version.publish(self.user)


class ServiceModelTests(ServicesTestBase):
    def test_content_str_returns_title(self):
        self.assertEqual(str(ServiceContent(title="Consulting")), "Consulting")

    def test_grouper_str_returns_content_title(self):
        service = self.create_service("Consulting", "consulting")
        self.assertEqual(str(service), "Consulting")

    def test_unsaved_grouper_str(self):
        self.assertEqual(str(Service()), "unsaved")

    def test_default_ordering_is_by_title(self):
        self.create_service("Bravo", "bravo")
        self.create_service("Alpha", "alpha")
        self.assertEqual(
            list(ServiceContent.objects.values_list("title", flat=True)),
            ["Alpha", "Bravo"],
        )

    def test_grouper_returns_its_own_content(self):
        first = self.create_service("Alpha", "alpha")
        second = self.create_service("Bravo", "bravo")
        self.assertEqual(first.get_content().title, "Alpha")
        self.assertEqual(second.get_content().title, "Bravo")


class ServiceVersioningConfigTests(ServicesTestBase):
    """``ServiceContent`` opts into versioning and frontend editing via ``CMSConfig``."""

    @property
    def config(self):
        return apps.get_app_config("djangocms_custom_content").cms_config

    def test_service_content_is_registered_as_grouper_content(self):
        grouper_model, grouper_field_name, has_language_field = self.config.custom_content_groupers[ServiceContent]
        self.assertIs(grouper_model, Service)
        self.assertEqual(grouper_field_name, "service")
        self.assertFalse(has_language_field)

    def test_service_content_is_versioned(self):
        versioned = [v.content_model for v in self.config.versioning]
        self.assertIn(ServiceContent, versioned)

    def test_service_content_is_frontend_editable(self):
        editable = [entry[0] for entry in self.config.cms_toolbar_enabled_models]
        self.assertIn(ServiceContent, editable)

    def test_service_grouper_is_in_admin_menu(self):
        self.assertIn(Service, self.config.admin_menu_models)

    def test_get_template_follows_the_default_convention(self):
        service = self.create_service("Consulting", "consulting")
        self.assertEqual(
            service.get_content().get_template(),
            "djangocms_custom_content_services/servicecontent_detail.html",
        )

    def test_creating_content_creates_a_version(self):
        from djangocms_versioning.constants import PUBLISHED
        from djangocms_versioning.models import Version

        service = self.create_service("Consulting", "consulting")

        version = Version.objects.filter_by_grouper(service).first()
        self.assertIsNotNone(version)
        self.assertEqual(version.state, PUBLISHED)

    def test_unpublished_content_is_hidden_from_the_default_manager(self):
        from djangocms_versioning.constants import PUBLISHED
        from djangocms_versioning.models import Version

        service = self.create_service("Consulting", "consulting")
        Version.objects.filter_by_grouper(service).filter(state=PUBLISHED).first().unpublish(self.user)

        self.assertFalse(ServiceContent.objects.filter(slug="consulting").exists())
        self.assertTrue(ServiceContent.admin_manager.filter(slug="consulting").exists())


class ServiceTeaserPluginTests(ServicesTestBase):
    def test_render_puts_the_services_content_in_context(self):
        """The plugin points at the grouper but the template renders its content."""
        service = self.create_service("Consulting", "consulting")
        instance = ServiceTeaser(service=service)

        context = ServiceTeaserPlugin().render({}, instance, "content")

        self.assertEqual(context["service"], service.get_content())
        self.assertEqual(context["service"].title, "Consulting")

    def test_render_distinguishes_services(self):
        """Two teasers must not resolve to the same content object."""
        first = ServiceTeaserPlugin().render({}, ServiceTeaser(service=self.create_service("Alpha", "alpha")), "c")
        second = ServiceTeaserPlugin().render({}, ServiceTeaser(service=self.create_service("Bravo", "bravo")), "c")

        self.assertEqual(first["service"].title, "Alpha")
        self.assertEqual(second["service"].title, "Bravo")


class FeaturedServicesPluginTests(ServicesTestBase):
    def setUp(self):
        self.featured = [self.create_service(f"Featured {i}", f"featured-{i}", is_featured=True) for i in range(3)]
        self.create_service("Plain", "plain", is_featured=False)

    def test_render_returns_only_featured_services(self):
        instance = FeaturedServices(limit=10)

        context = FeaturedServicesPlugin().render({}, instance, "content")

        self.assertEqual(
            {content.title for content in context["services"]},
            {"Featured 0", "Featured 1", "Featured 2"},
        )

    def test_render_respects_limit(self):
        instance = FeaturedServices(limit=2)

        context = FeaturedServicesPlugin().render({}, instance, "content")

        self.assertEqual(len(context["services"]), 2)
        self.assertTrue(all(content.is_featured for content in context["services"]))

    def test_render_skips_unpublished_services(self):
        """Only published content reaches the frontend."""
        from djangocms_versioning.constants import PUBLISHED
        from djangocms_versioning.models import Version

        Version.objects.filter_by_grouper(self.featured[0]).filter(state=PUBLISHED).first().unpublish(self.user)

        context = FeaturedServicesPlugin().render({}, FeaturedServices(limit=10), "content")

        self.assertEqual(
            {content.title for content in context["services"]},
            {"Featured 1", "Featured 2"},
        )
