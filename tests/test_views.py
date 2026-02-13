from unittest import skipUnless

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import connection
from django.http import Http404
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext

from djangocms_custom_content.contrib.people.models import Person, PersonContent
from djangocms_custom_content.views import (
    custom_detail_view_factory,
    render_frontend_editor,
)

User = get_user_model()
pytestmark = pytest.mark.django_db

VERSIONING = apps.is_installed("djangocms_versioning")


class _ToolbarStub:
    def __init__(self):
        self.obj = None

    def set_object(self, obj):
        self.obj = obj


class ViewsTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.superuser = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="password"
        )
        self.person = Person.objects.create()
        self.person_content = PersonContent.objects.with_user(self.superuser).create(
            person=self.person,
            name="Jane Doe",
            role="Developer",
            description="Test",
            slug="jane-doe",
        )

        # Publish content for versioning compatibility
        if VERSIONING:
            from djangocms_versioning.constants import DRAFT
            from djangocms_versioning.models import Version

            version = Version.objects.filter_by_grouper(self.person).filter(state=DRAFT).first()
            if version:
                version.publish(self.superuser)

    def test_custom_detail_view_factory_sets_model(self):
        view_class = custom_detail_view_factory(PersonContent)

        self.assertEqual(view_class.model, PersonContent)
        self.assertTrue(view_class.__name__.endswith("DetailView"))

    def test_custom_detail_view_get_queryset_selects_grouper(self):
        view_class = custom_detail_view_factory(PersonContent)
        view = view_class()

        queryset = view.get_queryset()
        select_related = queryset.query.select_related
        if isinstance(select_related, dict):
            self.assertIn("person", select_related)
        else:
            self.assertTrue(select_related)

    def test_frontend_editable_mixin_sets_toolbar_object(self):
        # For frontend editor, use draft content (no publish needed)
        view_class = custom_detail_view_factory(PersonContent)
        view = view_class()
        request = self.factory.get("/")
        request.toolbar = _ToolbarStub()

        # Use admin_manager to access all content including drafts
        view.setup(request, pk=self.person_content.pk)
        if VERSIONING:
            view.queryset = PersonContent.admin_manager.all()

        obj = view.get_object()

        self.assertEqual(obj, self.person_content)
        self.assertEqual(request.toolbar.obj, self.person_content)

    def test_render_frontend_editor_returns_template_response(self):
        request = self.factory.get("/")

        response = render_frontend_editor(request, self.person_content)

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.person_content._meta.model_name, response.context_data)
        self.assertEqual(response.context_data[self.person_content._meta.model_name], self.person_content)

    def test_detail_view_query_count_without_select_related(self):
        """Test query count for detail view without CustomDetailViewMixin."""
        from django.views.generic import DetailView

        view_class = type("PlainDetailView", (DetailView,), {"model": PersonContent})
        view = view_class()
        request = self.factory.get("/")
        view.setup(request, pk=self.person_content.pk)

        with CaptureQueriesContext(connection) as ctx:
            obj = view.get_object()
            # Access the grouper to trigger lazy loading
            _ = obj.person

        # Without select_related: 1 query for PersonContent + 1 for Person
        self.assertEqual(len(ctx), 2)

    def test_detail_view_query_count_with_select_related(self):
        """Test query count for detail view with CustomDetailViewMixin."""
        view_class = custom_detail_view_factory(PersonContent)
        view = view_class()
        request = self.factory.get("/")
        view.setup(request, pk=self.person_content.pk)

        with CaptureQueriesContext(connection) as ctx:
            obj = view.get_object()
            # Access the grouper - should not trigger another query
            _ = obj.person

        # With select_related: 1 query for PersonContent + Person
        self.assertEqual(len(ctx), 1)

    @skipUnless(VERSIONING, "Only relevant with versioning")
    def test_detail_view_hides_unpublished_content(self):
        """Test that CustomDetailView does not show unpublished (draft) content."""
        # Create an unpublished person and content
        unpublished_person = Person.objects.create()
        unpublished_content = PersonContent.objects.with_user(self.superuser).create(
            person=unpublished_person,
            name="Draft Person",
            role="Secret",
            description="This is a draft",
            slug="draft-person",
        )

        # Verify it exists in admin_manager (all content)
        self.assertTrue(PersonContent.admin_manager.filter(pk=unpublished_content.pk).exists())

        # Try to access via CustomDetailView - should raise Http404
        view_class = custom_detail_view_factory(PersonContent)
        view = view_class()
        request = self.factory.get("/")
        view.setup(request, pk=unpublished_content.pk)

        # Should raise Http404 because content is not published
        with self.assertRaises(Http404):
            view.get_object()
