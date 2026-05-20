"""Tests for the sortable autocomplete admin field on CMSConfig.m2m relations."""

import json

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from djangocms_custom_content.forms import (
    CustomM2MField,
    M2MAutocompleteSelectMultiple,
    SortedAutocompleteSelectMultiple,
)
from tests.test_app.models import OtherTarget, RelTopic, StandaloneContent, TagTarget

User = get_user_model()
pytestmark = pytest.mark.django_db


def _login_superuser(client):
    user = User.objects.create_superuser(username="admin", email="a@b.com", password="pw")
    client.force_login(user)
    return user


class OrderingTestCase(TransactionTestCase):
    """The through-table's ``order`` column controls iteration order."""

    def setUp(self):
        self.topic = RelTopic.objects.create()
        self.a = TagTarget.objects.create(name="A")
        self.b = TagTarget.objects.create(name="B")
        self.c = TagTarget.objects.create(name="C")

    def test_add_preserves_insertion_order(self):
        self.topic.tags.add(self.b, self.a, self.c)
        self.assertEqual(list(self.topic.tags.all()), [self.b, self.a, self.c])

    def test_set_replaces_and_reorders(self):
        self.topic.tags.add(self.a, self.b, self.c)
        self.topic.tags.set([self.c, self.a])
        self.assertEqual(list(self.topic.tags.all()), [self.c, self.a])
        self.assertEqual(self.topic.tags.count(), 2)

    def test_set_updates_existing_rows_without_duplicates(self):
        self.topic.tags.add(self.a, self.b)
        # Re-set with overlapping members in new order
        self.topic.tags.set([self.b, self.a])
        self.assertEqual(list(self.topic.tags.all()), [self.b, self.a])

    def test_reverse_accessor_respects_owner_order(self):
        topic_two = RelTopic.objects.create()
        # Stagger so the rows have non-trivial orders on each side
        topic_two.tags.add(self.a)
        self.topic.tags.add(self.a, self.b)
        # The reverse accessor returns all owners holding self.a, irrespective
        # of which owner ordered it where — but both lookups should work.
        owners = list(self.a.reltopic_set.all())
        self.assertCountEqual(owners, [self.topic, topic_two])


class AutocompleteViewTestCase(TransactionTestCase):
    """The JSON autocomplete endpoint resolves a target model and filters by term."""

    def setUp(self):
        _login_superuser(self.client)
        self.foo = TagTarget.objects.create(name="Foo")
        self.bar = TagTarget.objects.create(name="Bar")
        self.url = reverse("admin:djangocms_custom_content_m2m_autocomplete")

    def test_returns_all_matching_rows(self):
        resp = self.client.get(self.url, {"app_label": "test_app", "model_name": "tagtarget"})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        ids = {r["id"] for r in data["results"]}
        self.assertEqual(ids, {str(self.foo.pk), str(self.bar.pk)})

    def test_filters_by_term(self):
        resp = self.client.get(
            self.url,
            {"app_label": "test_app", "model_name": "tagtarget", "term": "Foo"},
        )
        data = json.loads(resp.content)
        self.assertEqual([r["text"] for r in data["results"]], ["Foo"])

    def test_unknown_target_returns_404(self):
        resp = self.client.get(self.url, {"app_label": "test_app", "model_name": "nope"})
        self.assertEqual(resp.status_code, 404)

    def test_requires_staff_user(self):
        self.client.logout()
        resp = self.client.get(self.url, {"app_label": "test_app", "model_name": "tagtarget"})
        # staff_member_required redirects to login when anonymous
        self.assertIn(resp.status_code, (302, 403))


class WidgetTestCase(TestCase):
    """The sortable autocomplete widget exposes the right URL, classes, and assets."""

    def setUp(self):
        from django.contrib import admin

        self.widget = SortedAutocompleteSelectMultiple(TagTarget, admin.site)

    def test_url_points_to_framework_view(self):
        self.assertEqual(
            self.widget.get_url(),
            reverse("admin:djangocms_custom_content_m2m_autocomplete"),
        )

    def test_build_attrs_includes_sortable_marker_class(self):
        attrs = self.widget.build_attrs({})
        self.assertIn("djangocms-custom-content-m2m-sortable", attrs["class"])
        self.assertIn("admin-autocomplete", attrs["class"])

    def test_media_includes_sortable_and_init_js(self):
        media_str = str(self.widget.media)
        self.assertIn("djangocms_custom_content/js/Sortable.min.js", media_str)
        self.assertIn("djangocms_custom_content/js/m2m-sortable.js", media_str)

    def test_optgroups_preserve_submitted_order(self):
        c = TagTarget.objects.create(name="C")
        a = TagTarget.objects.create(name="A")
        b = TagTarget.objects.create(name="B")
        # Submit order: c, a, b
        value = [str(c.pk), str(a.pk), str(b.pk)]
        field = CustomM2MField(TagTarget, admin_site=__import__("django.contrib.admin").contrib.admin.site)
        # Reuse the field's queryset choices for the widget
        widget = field.widget
        widget.choices = field.choices
        groups = widget.optgroups("tags", value)
        rendered_values = [str(opt["value"]) for _g, subgroup, _i in groups for opt in subgroup]
        self.assertEqual(rendered_values, [str(c.pk), str(a.pk), str(b.pk)])


class NonSortableWidgetTestCase(TestCase):
    """The default (non-sortable) widget omits Sortable.js + the marker class."""

    def setUp(self):
        from django.contrib import admin

        self.widget = M2MAutocompleteSelectMultiple(TagTarget, admin.site)

    def test_url_points_to_framework_view(self):
        self.assertEqual(
            self.widget.get_url(),
            reverse("admin:djangocms_custom_content_m2m_autocomplete"),
        )

    def test_no_sortable_marker_class(self):
        attrs = self.widget.build_attrs({})
        self.assertNotIn("djangocms-custom-content-m2m-sortable", attrs["class"])
        self.assertIn("admin-autocomplete", attrs["class"])

    def test_media_omits_sortable_assets(self):
        media_str = str(self.widget.media)
        self.assertNotIn("Sortable.min.js", media_str)
        self.assertNotIn("m2m-sortable.js", media_str)


class CustomM2MFieldTestCase(TestCase):
    """The form field validates and returns target objects (ordered when sortable)."""

    def setUp(self):
        from django.contrib import admin

        self.admin_site = admin.site
        self.a = TagTarget.objects.create(name="A")
        self.b = TagTarget.objects.create(name="B")

    def test_sortable_clean_returns_ordered_list(self):
        field = CustomM2MField(TagTarget, admin_site=self.admin_site, sortable=True)
        cleaned = field.clean([str(self.b.pk), str(self.a.pk)])
        self.assertEqual(cleaned, [self.b, self.a])

    def test_default_field_is_not_sortable(self):
        field = CustomM2MField(TagTarget, admin_site=self.admin_site)
        self.assertFalse(field.sortable)
        self.assertIsInstance(field.widget, M2MAutocompleteSelectMultiple)
        self.assertNotIsInstance(field.widget, SortedAutocompleteSelectMultiple)

    def test_empty_value_cleans_to_empty_list(self):
        field = CustomM2MField(TagTarget, admin_site=self.admin_site)
        self.assertEqual(field.clean([]), [])


class AdminMixinIntegrationTestCase(TransactionTestCase):
    """Saving a model through the admin persists m2m order via the mixin."""

    def setUp(self):
        _login_superuser(self.client)
        self.t1 = TagTarget.objects.create(name="T1")
        self.t2 = TagTarget.objects.create(name="T2")
        self.t3 = TagTarget.objects.create(name="T3")

    def test_add_view_renders_with_m2m_field(self):
        url = reverse("admin:test_app_reltopic_add")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        # The mixin should expose all three declared fields.
        for name in ("tags", "featured", "hidden"):
            self.assertIn(f'name="{name}"', content)

    def test_save_persists_chosen_order(self):
        add_url = reverse("admin:test_app_reltopic_add")
        resp = self.client.post(
            add_url,
            {
                "tags": [str(self.t3.pk), str(self.t1.pk), str(self.t2.pk)],
                "featured": [],
                "hidden": [],
            },
            follow=False,
        )
        # Either a redirect (success) or 200 with errors — verify the record.
        self.assertEqual(RelTopic.objects.count(), 1, msg=resp.content[:500])
        topic = RelTopic.objects.first()
        self.assertEqual(list(topic.tags.all()), [self.t3, self.t1, self.t2])

    def test_save_updates_order_on_existing_topic(self):
        topic = RelTopic.objects.create()
        topic.tags.add(self.t1, self.t2, self.t3)
        change_url = reverse("admin:test_app_reltopic_change", args=(topic.pk,))
        # Reorder to t2, t3, t1
        resp = self.client.post(
            change_url,
            {
                "tags": [str(self.t2.pk), str(self.t3.pk), str(self.t1.pk)],
                "featured": [],
                "hidden": [],
            },
            follow=False,
        )
        topic.refresh_from_db()
        self.assertEqual(list(topic.tags.all()), [self.t2, self.t3, self.t1], msg=resp.content[:500])

    def test_save_removes_relations_dropped_from_form(self):
        topic = RelTopic.objects.create()
        topic.tags.add(self.t1, self.t2, self.t3)
        change_url = reverse("admin:test_app_reltopic_change", args=(topic.pk,))
        self.client.post(
            change_url,
            {"tags": [str(self.t2.pk)], "featured": [], "hidden": []},
            follow=False,
        )
        topic.refresh_from_db()
        self.assertEqual(list(topic.tags.all()), [self.t2])

    def test_sortable_and_nonsortable_render_differently(self):
        """`m2m_sortable_fields` ships Sortable.js; `m2m_fields` does not."""
        url = reverse("admin:test_app_reltopic_add")
        resp = self.client.get(url)
        content = resp.content.decode()
        # `tags` is in m2m_sortable_fields → marker class present
        self.assertIn("djangocms-custom-content-m2m-sortable", content)
        # `featured` and `hidden` are in m2m_fields → they must NOT render
        # inside an element carrying the sortable marker. The crude check below
        # is enough because the marker class only appears via the sortable
        # widget's build_attrs.
        self.assertIn('name="featured"', content)
        self.assertIn('name="hidden"', content)
        # Only one sortable marker (from `tags`), not three.
        self.assertEqual(content.count("djangocms-custom-content-m2m-sortable"), 1)

    def test_nonsortable_field_persists_via_set(self):
        topic = RelTopic.objects.create()
        change_url = reverse("admin:test_app_reltopic_change", args=(topic.pk,))
        other = OtherTarget.objects.create(label="O1")
        other2 = OtherTarget.objects.create(label="O2")
        self.client.post(
            change_url,
            {
                "tags": [],
                "featured": [],
                "hidden": [str(other.pk), str(other2.pk)],
            },
            follow=False,
        )
        topic.refresh_from_db()
        self.assertCountEqual(list(topic.hidden.all()), [other, other2])

    def test_grouperless_admin_works_too(self):
        """StandaloneContent (no grouper) supports the mixin the same way."""
        add_url = reverse("admin:test_app_standalonecontent_add")
        resp = self.client.post(
            add_url,
            {"title": "hello", "targets": [str(self.t2.pk), str(self.t1.pk)]},
            follow=False,
        )
        self.assertEqual(StandaloneContent.objects.count(), 1, msg=resp.content[:500])
        sc = StandaloneContent.objects.first()
        self.assertEqual(list(sc.targets.all()), [self.t2, self.t1])
