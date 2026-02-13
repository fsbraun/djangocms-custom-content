import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from djangocms_custom_content.contrib.people.models import Person, PersonContent
from djangocms_custom_content.views import (
    custom_detail_view_factory,
    render_frontend_editor,
)

User = get_user_model()
pytestmark = pytest.mark.django_db


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
        view_class = custom_detail_view_factory(PersonContent)
        view = view_class()
        request = self.factory.get("/")
        request.toolbar = _ToolbarStub()
        view.request = request
        view.kwargs = {"pk": self.person_content.pk}

        obj = view.get_object()

        self.assertEqual(obj, self.person_content)
        self.assertEqual(request.toolbar.obj, self.person_content)

    def test_render_frontend_editor_returns_template_response(self):
        request = self.factory.get("/")

        response = render_frontend_editor(request, self.person_content)

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.person_content._meta.model_name, response.context_data)
        self.assertEqual(response.context_data[self.person_content._meta.model_name], self.person_content)
