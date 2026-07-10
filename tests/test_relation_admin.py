"""Tests for the admin autocomplete integration of relation fields."""

import json

import pytest
from django.contrib.admin import site
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from djangocms_custom_content.contrib.blog.admin import BlogPostAdmin
from djangocms_custom_content.contrib.blog.models import BlogPost, BlogPostContent
from djangocms_custom_content.contrib.categories.models import FlatCategory
from djangocms_custom_content.contrib.people.models import Person, PersonContent
from djangocms_custom_content.forms import OrderedModelMultipleChoiceField
from djangocms_custom_content.relation_admin import (
    RelationAutocompleteSelectMultiple,
    SortedRelationAutocompleteSelectMultiple,
)

User = get_user_model()
pytestmark = pytest.mark.django_db


class AdminRelationTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser("admin", "admin@example.com", "pw")

    def setUp(self):
        self.admin = BlogPostAdmin(BlogPost, site)
        self.rf = RequestFactory()

    def _request(self):
        request = self.rf.get("/")
        request.user = self.user
        return request

    def _post(self):
        post = BlogPost.objects.create()
        BlogPostContent.objects.with_user(self.user).create(
            post=post, title="P", slug="p", excerpt="", body="", language="en"
        )
        return post

    def _person(self, name, slug):
        person = Person.objects.create()
        PersonContent.objects.with_user(self.user).create(person=person, name=name, role="", description="", slug=slug)
        return person


class FormInjectionTests(AdminRelationTestBase):
    def test_relation_fields_detected(self):
        self.assertEqual(set(self.admin._relation_fields()), {"authors", "categories"})

    def test_autocomplete_url_registered(self):
        names = [u.name for u in self.admin.get_urls() if u.name]
        self.assertIn("djangocms_custom_content_blog_blogpost_relation_autocomplete", names)

    def test_form_gets_relation_fields_with_widgets(self):
        form_class = self.admin.get_form(self._request(), None)
        self.assertIn("authors", form_class.base_fields)
        self.assertIn("categories", form_class.base_fields)
        # ordered -> sorted widget + order-preserving field
        authors = form_class.base_fields["authors"]
        self.assertIsInstance(authors.widget, SortedRelationAutocompleteSelectMultiple)
        self.assertIsInstance(authors, OrderedModelMultipleChoiceField)
        # unordered -> plain autocomplete widget
        categories = form_class.base_fields["categories"]
        self.assertIsInstance(categories.widget, RelationAutocompleteSelectMultiple)
        self.assertNotIsInstance(categories.widget, SortedRelationAutocompleteSelectMultiple)

    def test_initial_populated_from_instance(self):
        post = self._post()
        ann, bob = self._person("Ann", "ann"), self._person("Bob", "bob")
        post.authors.add(bob, ann)  # stored order: bob, ann
        request = self._request()
        self.admin.get_grouping_from_request(request)
        form_class = self.admin.get_form(request, post)
        form = form_class(instance=post)
        self.assertEqual(list(form.initial["authors"]), [bob.pk, ann.pk])

    def test_sorted_widget_pulls_in_js(self):
        form_class = self.admin.get_form(self._request(), None)
        js = [str(entry) for entry in form_class.base_fields["authors"].widget.media._js]
        self.assertTrue(any("Sortable.min.js" in j for j in js))
        self.assertTrue(any("sorted-autocomplete.js" in j for j in js))


class AutocompleteEndpointTests(AdminRelationTestBase):
    def test_returns_matching_targets(self):
        self._person("Alice", "alice")
        self._person("Zoe", "zoe")
        request = self.rf.get("/", {"field_name": "authors", "term": "Ali"})
        request.user = self.user
        response = self.admin.relation_autocomplete_view(request)
        data = json.loads(response.content)
        labels = [r["text"] for r in data["results"]]
        self.assertIn("Alice", labels)
        self.assertNotIn("Zoe", labels)

    def test_unknown_field_returns_empty(self):
        request = self.rf.get("/", {"field_name": "nope", "term": ""})
        request.user = self.user
        data = json.loads(self.admin.relation_autocomplete_view(request).content)
        self.assertEqual(data["results"], [])

    def test_categories_endpoint(self):
        FlatCategory.objects.create(title="News", slug="news")
        request = self.rf.get("/", {"field_name": "categories", "term": "New"})
        request.user = self.user
        data = json.loads(self.admin.relation_autocomplete_view(request).content)
        self.assertIn("News", [r["text"] for r in data["results"]])


class SaveAndOrderingTests(AdminRelationTestBase):
    def test_ordered_field_preserves_submitted_order(self):
        ann, bob, cara = self._person("Ann", "ann"), self._person("Bob", "bob"), self._person("Cara", "cara")
        field = OrderedModelMultipleChoiceField(queryset=Person.objects.all())
        # submit in a non-database order
        cleaned = field.clean([str(cara.pk), str(ann.pk), str(bob.pk)])
        self.assertEqual([o.pk for o in cleaned], [cara.pk, ann.pk, bob.pk])

    def test_sorted_widget_renders_selected_in_value_order(self):
        ann, bob = self._person("Ann", "ann"), self._person("Bob", "bob")
        form_class = self.admin.get_form(self._request(), None)
        widget = form_class.base_fields["authors"].widget
        # value order bob, ann should be reflected in option order
        groups = widget.optgroups("authors", [str(bob.pk), str(ann.pk)])
        values = [opt["value"] for _g, sub, _i in groups for opt in sub]
        self.assertEqual(values, [bob.pk, ann.pk])
