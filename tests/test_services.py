"""Tests for the Services example contrib app.

Covers the ``Service`` model and the two plugins' ``render()`` logic. The render
methods are exercised directly (with unsaved plugin instances and a plain context
dict) rather than via full template rendering, so the context-building branches
are tested without depending on project templates.
"""

import pytest
from django.test import TestCase

from djangocms_custom_content.contrib.services.cms_plugins import (
    FeaturedServicesPlugin,
    ServiceTeaserPlugin,
)
from djangocms_custom_content.contrib.services.models import (
    FeaturedServices,
    Service,
    ServiceTeaser,
)

pytestmark = pytest.mark.django_db


class ServiceModelTests(TestCase):
    def test_str_returns_title(self):
        self.assertEqual(str(Service(title="Consulting")), "Consulting")

    def test_default_ordering_is_by_title(self):
        Service.objects.create(title="Bravo", slug="bravo")
        Service.objects.create(title="Alpha", slug="alpha")
        self.assertEqual(
            list(Service.objects.values_list("title", flat=True)),
            ["Alpha", "Bravo"],
        )


class ServiceTeaserPluginTests(TestCase):
    def test_render_puts_service_in_context(self):
        service = Service.objects.create(title="Consulting", slug="consulting")
        instance = ServiceTeaser(service=service)
        context = ServiceTeaserPlugin().render({}, instance, "content")
        self.assertEqual(context["service"], service)


class FeaturedServicesPluginTests(TestCase):
    def setUp(self):
        self.featured = [
            Service.objects.create(title=f"Featured {i}", slug=f"featured-{i}", is_featured=True) for i in range(3)
        ]
        Service.objects.create(title="Plain", slug="plain", is_featured=False)

    def test_render_returns_only_featured_services(self):
        instance = FeaturedServices(limit=10)
        context = FeaturedServicesPlugin().render({}, instance, "content")
        self.assertEqual(set(context["services"]), set(self.featured))

    def test_render_respects_limit(self):
        instance = FeaturedServices(limit=2)
        context = FeaturedServicesPlugin().render({}, instance, "content")
        self.assertEqual(len(context["services"]), 2)
        self.assertTrue(all(s.is_featured for s in context["services"]))
