"""Tests for the unified CMSConfig.m2m API."""

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.test import TestCase, TransactionTestCase

from djangocms_custom_content.models import (
    AbstractCustomRelation,
    _CustomM2MManager,
)
from tests.test_app.models import (
    OtherTarget,
    RelTopic,
    RelTopicContent,
    StandaloneContent,
    TagTarget,
)

User = get_user_model()
pytestmark = pytest.mark.django_db


class ThroughModelGenerationTestCase(TestCase):
    """The framework must auto-generate the through-model from CMSConfig.m2m."""

    def test_through_model_exists_for_grouped_content(self):
        through = apps.get_model("test_app", "RelTopicContentRelation")
        self.assertTrue(issubclass(through, AbstractCustomRelation))

    def test_through_model_instance_fk_targets_grouper(self):
        through = apps.get_model("test_app", "RelTopicContentRelation")
        instance_field = through._meta.get_field("instance")
        self.assertIsInstance(instance_field, models.ForeignKey)
        self.assertEqual(instance_field.related_model, RelTopic)

    def test_through_model_for_grouperless_content_targets_self(self):
        through = apps.get_model("test_app", "StandaloneContentRelation")
        instance_field = through._meta.get_field("instance")
        self.assertEqual(instance_field.related_model, StandaloneContent)

    def test_through_model_has_required_columns(self):
        through = apps.get_model("test_app", "RelTopicContentRelation")
        for field_name in ("instance", "content_type", "object_id", "relation_name"):
            self.assertTrue(through._meta.get_field(field_name))


class DescriptorPlacementTestCase(TestCase):
    """Forward accessors land on the grouper (or content if grouperless);
    reverse accessors land on the target unless suppressed."""

    def test_forward_accessor_lives_on_grouper(self):
        topic = RelTopic.objects.create()
        self.assertTrue(hasattr(topic, "tags"))
        self.assertTrue(hasattr(topic, "featured"))
        self.assertTrue(hasattr(topic, "hidden"))

    def test_forward_accessor_lives_on_content_when_no_grouper(self):
        content = StandaloneContent.objects.create(title="x")
        self.assertTrue(hasattr(content, "targets"))

    def test_auto_reverse_name_uses_owner_model_name(self):
        tag = TagTarget.objects.create(name="t")
        # auto reverse name is "{owner_model_name}_set" = "reltopic_set"
        self.assertTrue(hasattr(tag, "reltopic_set"))

    def test_explicit_reverse_name_is_used(self):
        tag = TagTarget.objects.create(name="t")
        self.assertTrue(hasattr(tag, "featured_in"))

    def test_reverse_name_can_be_suppressed_with_none(self):
        # The "hidden" relation declared its reverse as None — OtherTarget
        # should NOT carry an auto-generated reverse accessor.
        target = OtherTarget.objects.create(label="x")
        # Nothing automatically named for the suppressed relation
        self.assertFalse(hasattr(target, "reltopic_set"))
        self.assertFalse(hasattr(target, "hidden"))


class ForwardManagerTestCase(TransactionTestCase):
    """Adding/removing/clearing/listing via the forward accessor."""

    def setUp(self):
        self.topic = RelTopic.objects.create()
        self.tag_a = TagTarget.objects.create(name="A")
        self.tag_b = TagTarget.objects.create(name="B")

    def test_manager_type(self):
        self.assertIsInstance(self.topic.tags, _CustomM2MManager)

    def test_initially_empty(self):
        self.assertEqual(list(self.topic.tags.all()), [])
        self.assertEqual(self.topic.tags.count(), 0)
        self.assertFalse(self.topic.tags.exists())

    def test_add_then_list(self):
        self.topic.tags.add(self.tag_a, self.tag_b)
        related = list(self.topic.tags.all())
        self.assertCountEqual(related, [self.tag_a, self.tag_b])

    def test_add_is_idempotent(self):
        self.topic.tags.add(self.tag_a)
        self.topic.tags.add(self.tag_a)
        self.assertEqual(self.topic.tags.count(), 1)

    def test_remove(self):
        self.topic.tags.add(self.tag_a, self.tag_b)
        self.topic.tags.remove(self.tag_a)
        self.assertCountEqual(list(self.topic.tags.all()), [self.tag_b])

    def test_clear(self):
        self.topic.tags.add(self.tag_a, self.tag_b)
        self.topic.tags.clear()
        self.assertFalse(self.topic.tags.exists())


class ReverseManagerTestCase(TransactionTestCase):
    """The reverse accessor returns owner instances filtered by relation_name."""

    def setUp(self):
        self.topic_one = RelTopic.objects.create()
        self.topic_two = RelTopic.objects.create()
        self.tag = TagTarget.objects.create(name="A")

    def test_reverse_lists_owners(self):
        self.topic_one.tags.add(self.tag)
        self.topic_two.tags.add(self.tag)
        self.assertCountEqual(list(self.tag.reltopic_set.all()), [self.topic_one, self.topic_two])

    def test_reverse_add_from_target_side(self):
        self.tag.reltopic_set.add(self.topic_one)
        self.assertIn(self.tag, list(self.topic_one.tags.all()))

    def test_reverse_remove(self):
        self.topic_one.tags.add(self.tag)
        self.tag.reltopic_set.remove(self.topic_one)
        self.assertFalse(self.topic_one.tags.exists())


class MultipleRelationsToSameTargetTestCase(TransactionTestCase):
    """Two m2m fields pointing at the same target model must stay independent."""

    def setUp(self):
        self.topic = RelTopic.objects.create()
        self.tag = TagTarget.objects.create(name="A")

    def test_tags_and_featured_are_independent(self):
        self.topic.tags.add(self.tag)
        self.assertEqual(self.topic.tags.count(), 1)
        self.assertEqual(self.topic.featured.count(), 0)

        self.topic.featured.add(self.tag)
        self.assertEqual(self.topic.featured.count(), 1)
        self.assertEqual(self.topic.tags.count(), 1)

    def test_relation_name_is_stored_on_through_row(self):
        through = apps.get_model("test_app", "RelTopicContentRelation")
        self.topic.tags.add(self.tag)
        self.topic.featured.add(self.tag)
        names = set(through.objects.values_list("relation_name", flat=True))
        self.assertEqual(names, {"tags", "featured"})

    def test_reverse_accessors_are_distinct(self):
        self.topic.tags.add(self.tag)
        self.assertCountEqual(list(self.tag.reltopic_set.all()), [self.topic])
        self.assertCountEqual(list(self.tag.featured_in.all()), [])


class SuppressedReverseTestCase(TransactionTestCase):
    """A relation declared with reverse=None still works one-way."""

    def setUp(self):
        self.topic = RelTopic.objects.create()
        self.other = OtherTarget.objects.create(label="hidden-target")

    def test_forward_still_works(self):
        self.topic.hidden.add(self.other)
        self.assertCountEqual(list(self.topic.hidden.all()), [self.other])

    def test_no_reverse_was_installed(self):
        self.assertFalse(hasattr(self.other, "reltopic_set"))


class GrouperlessContentTestCase(TransactionTestCase):
    """Content models without a grouper own their own relations."""

    def setUp(self):
        self.content = StandaloneContent.objects.create(title="x")
        self.tag = TagTarget.objects.create(name="t")

    def test_forward_add_and_list(self):
        self.content.targets.add(self.tag)
        self.assertCountEqual(list(self.content.targets.all()), [self.tag])

    def test_auto_reverse_uses_content_model_name(self):
        # Owner is StandaloneContent (no grouper), so reverse is standalonecontent_set
        self.content.targets.add(self.tag)
        self.assertCountEqual(list(self.tag.standalonecontent_set.all()), [self.content])


class BlogContribIntegrationTestCase(TransactionTestCase):
    """End-to-end: contrib blog declares the new m2m API."""

    def setUp(self):
        from djangocms_custom_content.contrib.blog.models import BlogPost, BlogPostContent
        from djangocms_custom_content.contrib.categories.models import FlatCategory
        from djangocms_custom_content.contrib.people.models import Person, PersonContent

        self.BlogPost = BlogPost
        self.BlogPostContent = BlogPostContent
        self.FlatCategory = FlatCategory
        self.Person = Person
        self.PersonContent = PersonContent

        self.superuser = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="password",
        )

        self.blog_post = BlogPost.objects.create()
        BlogPostContent.objects.with_user(self.superuser).create(
            post=self.blog_post,
            title="Hello",
            slug="hello",
            language="en",
        )
        self.person = Person.objects.create()
        PersonContent.objects.with_user(self.superuser).create(
            person=self.person,
            name="Alice",
            slug="alice",
        )
        self.category = FlatCategory.objects.create(title="Tech", slug="tech")

    def test_blog_post_has_authors_and_categories(self):
        self.assertTrue(hasattr(self.blog_post, "authors"))
        self.assertTrue(hasattr(self.blog_post, "categories"))

    def test_add_author_and_category(self):
        self.blog_post.authors.add(self.person)
        self.blog_post.categories.add(self.category)

        self.assertCountEqual(list(self.blog_post.authors.all()), [self.person])
        self.assertCountEqual(list(self.blog_post.categories.all()), [self.category])

    def test_auto_reverse_on_targets(self):
        self.blog_post.authors.add(self.person)
        self.blog_post.categories.add(self.category)

        self.assertCountEqual(list(self.person.blogpost_set.all()), [self.blog_post])
        self.assertCountEqual(list(self.category.blogpost_set.all()), [self.blog_post])


class MissingTargetModelTestCase(TransactionTestCase):
    """m2m entries pointing at uninstalled or malformed targets must be ignored."""

    def setUp(self):
        self.topic = RelTopic.objects.create()

    def test_uninstalled_target_returns_dummy_manager(self):
        # nonexistent_app.Ghost is not installed — accessor exists but is no-op
        self.assertTrue(hasattr(self.topic, "ghosts"))
        self.assertEqual(self.topic.ghosts.all(), [])
        self.assertEqual(self.topic.ghosts.count(), 0)
        self.assertFalse(self.topic.ghosts.exists())

    def test_uninstalled_target_writes_are_no_ops(self):
        # add / remove / clear shouldn't crash, shouldn't write any rows
        self.topic.ghosts.add("anything")  # would crash on a real manager
        self.topic.ghosts.remove("anything")
        self.topic.ghosts.clear()
        self.assertFalse(self.topic.ghosts.exists())

    def test_malformed_label_is_also_ignored(self):
        # "no_dot_here" has no app.Model shape — also fed to the dummy path
        self.assertTrue(hasattr(self.topic, "malformed"))
        self.assertEqual(self.topic.malformed.all(), [])

    def test_through_model_still_created(self):
        # The through-model is local to the declaring app and must exist even
        # when every relation's target is missing.
        through = apps.get_model("test_app", "RelTopicContentRelation")
        self.assertIsNotNone(through)

    def test_resolvable_relations_still_work_alongside_missing(self):
        # The presence of unresolvable entries must not break resolvable ones.
        tag = TagTarget.objects.create(name="x")
        self.topic.tags.add(tag)
        self.assertCountEqual(list(self.topic.tags.all()), [tag])


class AbstractRelationStructureTestCase(TestCase):
    """The auto-generated through-model carries the expected fields and behavior."""

    def test_abstract_relation_is_abstract(self):
        self.assertTrue(AbstractCustomRelation._meta.abstract)

    def test_concrete_relation_has_content_type(self):
        through = apps.get_model("test_app", "RelTopicContentRelation")
        field = through._meta.get_field("content_type")
        self.assertEqual(field.related_model, ContentType)

    def test_concrete_relation_has_object_id(self):
        through = apps.get_model("test_app", "RelTopicContentRelation")
        field = through._meta.get_field("object_id")
        self.assertIsInstance(field, models.PositiveIntegerField)

    def test_concrete_relation_str(self):
        topic = RelTopic.objects.create()
        tag = TagTarget.objects.create(name="A")
        topic.tags.add(tag)
        through = apps.get_model("test_app", "RelTopicContentRelation")
        row = through.objects.first()
        rendered = str(row)
        self.assertIn("tags", rendered)
        self.assertIn(str(topic), rendered)
