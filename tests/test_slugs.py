"""Tests for the two fields the framework treats specially: ``slug`` and ``language``.

A detail URL has to identify a single content object. That needs the detail view to
narrow by the active language, and a slug not to be shared by two different objects.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils.translation import override

from djangocms_custom_content.contrib.blog.models import BlogPost, BlogPostContent
from djangocms_custom_content.contrib.people.models import Person, PersonContent
from djangocms_custom_content.views import custom_detail_view_factory

User = get_user_model()
pytestmark = pytest.mark.django_db


class SlugTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser("admin", "admin@example.com", "pw")

    def publish(self, grouper):
        """The detail view only sees published content."""
        from djangocms_versioning.constants import DRAFT
        from djangocms_versioning.models import Version

        for version in Version.objects.filter_by_grouper(grouper).filter(state=DRAFT):
            version.publish(self.user)
        return grouper

    def make_post(self, title, slug, language="en", post=None):
        post = post or BlogPost.objects.create()
        BlogPostContent.objects.with_user(self.user).create(
            post=post, title=title, slug=slug, excerpt="", body="", language=language
        )
        return self.publish(post)

    def make_person(self, name, slug, person=None):
        person = person or Person.objects.create()
        PersonContent.objects.with_user(self.user).create(person=person, slug=slug, name=name, role="", description="")
        return self.publish(person)

    def view_for(self, model, **kwargs):
        view = custom_detail_view_factory(model)()
        view.kwargs = kwargs
        view.request = None
        return view


class DetailViewLanguageTests(SlugTestBase):
    """``language`` scopes the lookup: one object has one content per language."""

    def test_active_language_selects_the_translation(self):
        post = self.make_post("Hello world", "hello-world", language="en")
        self.make_post("Hallo Welt", "hello-world", language="de", post=post)

        for language, expected in [("en", "Hello world"), ("de", "Hallo Welt")]:
            with override(language):
                view = self.view_for(BlogPostContent, slug="hello-world")
                self.assertEqual(view.get_object().title, expected)

    def test_translations_of_one_object_are_not_ambiguous(self):
        """Two translations share a slug by design and must not raise."""
        post = self.make_post("Hello world", "hello-world", language="en")
        self.make_post("Hallo Welt", "hello-world", language="de", post=post)

        with override("en"):
            view = self.view_for(BlogPostContent, slug="hello-world")
            with self.assertNoLogs("djangocms_custom_content.views", level="ERROR"):
                self.assertEqual(view.get_object().language, "en")

    def test_model_without_language_field_is_not_filtered(self):
        self.make_person("Ada Lovelace", "ada-lovelace")

        with override("de"):
            view = self.view_for(PersonContent, slug="ada-lovelace")
            self.assertEqual(view.get_object().name, "Ada Lovelace")


class DetailViewAmbiguousSlugTests(SlugTestBase):
    """A duplicate that slipped through is logged, not fatal."""

    def test_duplicate_slug_serves_first_and_logs(self):
        self.make_person("Ada Lovelace", "ada-lovelace")
        self.make_person("Ada L. (duplicate)", "ada-lovelace")

        view = self.view_for(PersonContent, slug="ada-lovelace")
        with self.assertLogs("djangocms_custom_content.views", level="ERROR") as logs:
            obj = view.get_object()

        self.assertIsNotNone(obj)
        self.assertEqual(obj.slug, "ada-lovelace")
        self.assertIn("matches more than one object", logs.output[0])
        self.assertIn("PersonContent", logs.output[0])

    def test_unknown_slug_still_raises_404(self):
        from django.http import Http404

        self.make_person("Ada Lovelace", "ada-lovelace")

        view = self.view_for(PersonContent, slug="nobody")
        with self.assertRaises(Http404):
            view.get_object()


class SlugConflictValidationTests(SlugTestBase):
    """``validate_unique`` keeps a slug bound to a single object."""

    def _clean(self, obj):
        obj.full_clean(exclude=["placeholders"])

    def test_another_object_may_not_reuse_a_slug(self):
        self.make_person("Ada Lovelace", "ada-lovelace")

        clash = PersonContent(person=Person.objects.create(), slug="ada-lovelace", name="Impostor")

        with self.assertRaises(ValidationError) as ctx:
            self._clean(clash)
        self.assertIn("slug", ctx.exception.message_dict)

    def test_same_object_may_reuse_its_own_slug(self):
        """New versions of one object share its slug."""
        person = self.make_person("Ada Lovelace", "ada-lovelace")

        self._clean(PersonContent(person=person, slug="ada-lovelace", name="Ada Lovelace"))

    def test_translation_of_one_object_may_reuse_its_slug(self):
        post = self.make_post("Hello world", "hello-world", language="en")

        self._clean(BlogPostContent(post=post, slug="hello-world", title="Hallo", language="de"))

    def test_conflict_is_scoped_to_the_language(self):
        """A slug taken in English does not block the same slug in German."""
        self.make_post("Hello world", "hello-world", language="en")

        self._clean(BlogPostContent(post=BlogPost.objects.create(), slug="hello-world", title="Hallo", language="de"))

    def test_conflict_within_one_language_is_rejected(self):
        self.make_post("Hello world", "hello-world", language="en")

        clash = BlogPostContent(post=BlogPost.objects.create(), slug="hello-world", title="X", language="en")

        with self.assertRaises(ValidationError) as ctx:
            self._clean(clash)
        self.assertIn("slug", ctx.exception.message_dict)

    def test_archived_versions_also_hold_their_slug(self):
        """Every version counts, not just the current one: reverting must stay safe."""
        person = self.make_person("Ada Lovelace", "ada-lovelace")
        PersonContent.admin_manager.filter(person=person).update(slug="ada-renamed")

        conflicts = PersonContent.find_slug_conflicts("ada-renamed", grouper_id=Person.objects.create().pk)

        self.assertTrue(conflicts.exists())

    def test_no_slug_no_conflict(self):
        self.assertFalse(PersonContent.find_slug_conflicts("").exists())
        self.assertFalse(PersonContent.find_slug_conflicts(None).exists())
