"""Tests for grouper-anchored relations (djangocms_custom_content.relations).

These cover the sound replacement for the legacy generic M2M:

- real queryset semantics on the accessors (filter / order_by / count / exists);
- optional ordering;
- content -> grouper normalisation on the input side;
- the invited reverse accessor;
- target-side cascade on delete;
- the headline property: relations survive a content version copy because they
  are anchored to the stable grouper pk, not the versioned content pk.
"""

import pytest
from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.test import TestCase

from djangocms_custom_content.contrib.blog.models import BlogPost, BlogPostContent
from djangocms_custom_content.contrib.categories.models import FlatCategory
from djangocms_custom_content.contrib.people.models import Person, PersonContent
from djangocms_custom_content.relations import grouper_model_of, grouper_of

User = get_user_model()
pytestmark = pytest.mark.django_db


class RelationTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser("admin", "admin@example.com", "pw")

    def _post(self, title="A post", slug="a-post"):
        post = BlogPost.objects.create()
        BlogPostContent.objects.with_user(self.user).create(
            post=post, title=title, slug=slug, excerpt="", body="", language="en"
        )
        return post

    def _person(self, name, slug):
        person = Person.objects.create()
        PersonContent.objects.with_user(self.user).create(person=person, name=name, role="", description="", slug=slug)
        return person


class GrouperResolutionTests(RelationTestBase):
    def test_grouper_model_of_content_returns_grouper(self):
        self.assertIs(grouper_model_of(BlogPostContent), BlogPost)
        self.assertIs(grouper_model_of(PersonContent), Person)

    def test_grouper_model_of_grouper_is_identity(self):
        self.assertIs(grouper_model_of(BlogPost), BlogPost)

    def test_grouper_of_content_instance_returns_grouper(self):
        person = self._person("Ann", "ann")
        content = PersonContent.admin_manager.filter(person=person).first()
        self.assertEqual(grouper_of(content), person)

    def test_grouper_of_grouper_instance_is_identity(self):
        person = self._person("Ann", "ann")
        self.assertEqual(grouper_of(person), person)


class ForwardAccessorTests(RelationTestBase):
    def setUp(self):
        self.post = self._post()
        self.ann = self._person("Ann", "ann")
        self.bob = self._person("Bob", "bob")

    def test_accessor_returns_real_queryset(self):
        self.post.authors.add(self.ann)
        self.assertIsInstance(self.post.authors.all(), QuerySet)
        self.assertIsInstance(self.post.authors.filter(pk=self.ann.pk), QuerySet)

    def test_add_and_all(self):
        self.post.authors.add(self.ann, self.bob)
        self.assertEqual(set(self.post.authors.all()), {self.ann, self.bob})

    def test_add_is_idempotent(self):
        self.post.authors.add(self.ann)
        self.post.authors.add(self.ann)
        self.assertEqual(self.post.authors.count(), 1)

    def test_bulk_add_deduplicates_inputs(self):
        self.post.authors.add(self.ann, self.ann, self.bob)
        self.assertEqual(list(self.post.authors.all()), [self.ann, self.bob])

    def test_add_rejects_unsaved_objects(self):
        with self.assertRaisesMessage(ValueError, "saved model instances"):
            self.post.authors.add(Person())

    def test_remove(self):
        self.post.authors.add(self.ann, self.bob)
        self.post.authors.remove(self.ann)
        self.assertEqual(set(self.post.authors.all()), {self.bob})

    def test_set_replaces(self):
        self.post.authors.add(self.ann)
        self.post.authors.set([self.bob])
        self.assertEqual(set(self.post.authors.all()), {self.bob})

    def test_set_preserves_existing_edges(self):
        self.post.authors.add(self.ann, self.bob)
        through = BlogPost.authors.field.through
        ann_edge_pk = through.objects.get(source=self.post, object_id=self.ann.pk).pk

        self.post.authors.set([self.bob, self.ann])

        self.assertEqual(through.objects.get(source=self.post, object_id=self.ann.pk).pk, ann_edge_pk)
        self.assertEqual(list(self.post.authors.all()), [self.bob, self.ann])

    def test_clear(self):
        self.post.authors.add(self.ann, self.bob)
        self.post.authors.clear()
        self.assertFalse(self.post.authors.exists())

    def test_queryset_methods_work(self):
        self.post.authors.add(self.ann, self.bob)
        self.assertEqual(self.post.authors.count(), 2)
        self.assertTrue(self.post.authors.exists())
        # .filter() chains onto a real queryset of Person groupers
        filtered = self.post.authors.filter(pk=self.ann.pk)
        self.assertIsInstance(filtered, QuerySet)
        self.assertEqual(list(filtered), [self.ann])

    def test_iteration(self):
        self.post.authors.add(self.ann, self.bob)
        self.assertEqual(set(iter(self.post.authors)), {self.ann, self.bob})

    def test_accepts_content_object_and_stores_grouper(self):
        ann_content = PersonContent.admin_manager.filter(person=self.ann).first()
        self.post.authors.add(ann_content)  # pass content, not grouper
        self.assertEqual(set(self.post.authors.all()), {self.ann})


class OrderingTests(RelationTestBase):
    def setUp(self):
        self.post = self._post()
        self.ann = self._person("Ann", "ann")
        self.bob = self._person("Bob", "bob")
        self.cara = self._person("Cara", "cara")

    def test_order_follows_insertion(self):
        self.post.authors.add(self.bob, self.ann, self.cara)
        self.assertEqual(list(self.post.authors.all()), [self.bob, self.ann, self.cara])

    def test_reorder(self):
        self.post.authors.add(self.bob, self.ann, self.cara)
        self.post.authors.reorder([self.cara, self.ann, self.bob])
        self.assertEqual(list(self.post.authors.all()), [self.cara, self.ann, self.bob])

    def test_reorder_deduplicates_inputs(self):
        self.post.authors.add(self.ann, self.bob)
        through = BlogPost.authors.field.through
        ann_edge_pk = through.objects.get(source=self.post, object_id=self.ann.pk).pk
        bob_edge_pk = through.objects.get(source=self.post, object_id=self.bob.pk).pk

        self.post.authors.reorder([self.ann, self.ann, self.bob])

        self.assertEqual(through.objects.filter(source=self.post).count(), 2)
        self.assertEqual(list(self.post.authors.all()), [self.ann, self.bob])
        self.assertEqual(
            {
                through.objects.get(source=self.post, object_id=self.ann.pk).pk,
                through.objects.get(source=self.post, object_id=self.bob.pk).pk,
            },
            {ann_edge_pk, bob_edge_pk},
        )

    def test_reorder_empty_iterable_preserves_existing_edges(self):
        self.post.authors.add(self.ann, self.bob)
        through = BlogPost.authors.field.through
        ann_edge_pk = through.objects.get(source=self.post, object_id=self.ann.pk).pk
        bob_edge_pk = through.objects.get(source=self.post, object_id=self.bob.pk).pk

        self.post.authors.reorder([])

        self.assertEqual(
            {
                through.objects.get(source=self.post, object_id=self.ann.pk).pk,
                through.objects.get(source=self.post, object_id=self.bob.pk).pk,
            },
            {ann_edge_pk, bob_edge_pk},
        )
        self.assertEqual(list(self.post.authors.all()), [self.ann, self.bob])


class ReverseAccessorTests(RelationTestBase):
    def setUp(self):
        self.ann = self._person("Ann", "ann")
        self.post1 = self._post("One", "one")
        self.post2 = self._post("Two", "two")

    def test_reverse_accessor_exists_on_target(self):
        self.assertTrue(hasattr(self.ann, "authored_posts"))

    def test_reverse_returns_sources(self):
        self.post1.authors.add(self.ann)
        self.post2.authors.add(self.ann)
        self.assertEqual(set(self.ann.authored_posts.all()), {self.post1, self.post2})

    def test_reverse_is_real_queryset(self):
        self.post1.authors.add(self.ann)
        self.assertIsInstance(self.ann.authored_posts.all(), QuerySet)

    def test_reverse_filter_chains_onto_real_queryset(self):
        self.post1.authors.add(self.ann)
        self.post2.authors.add(self.ann)
        filtered = self.ann.authored_posts.filter(pk=self.post1.pk)
        self.assertIsInstance(filtered, QuerySet)
        self.assertEqual(list(filtered), [self.post1])

    def test_reverse_count_and_exists(self):
        self.assertFalse(self.ann.authored_posts.exists())
        self.assertEqual(self.ann.authored_posts.count(), 0)
        self.post1.authors.add(self.ann)
        self.post2.authors.add(self.ann)
        self.assertTrue(self.ann.authored_posts.exists())
        self.assertEqual(self.ann.authored_posts.count(), 2)

    def test_reverse_iteration(self):
        self.post1.authors.add(self.ann)
        self.post2.authors.add(self.ann)
        self.assertEqual(set(iter(self.ann.authored_posts)), {self.post1, self.post2})

    def test_reverse_add(self):
        self.ann.authored_posts.add(self.post1, self.post2)
        # Reverse add is symmetric with forward add: the edge resolves both ways.
        self.assertEqual(set(self.ann.authored_posts.all()), {self.post1, self.post2})
        self.assertEqual(set(self.post1.authors.all()), {self.ann})

    def test_reverse_add_is_idempotent(self):
        self.ann.authored_posts.add(self.post1)
        self.ann.authored_posts.add(self.post1)
        self.assertEqual(self.ann.authored_posts.count(), 1)

    def test_reverse_bulk_add_deduplicates_inputs(self):
        self.ann.authored_posts.add(self.post1, self.post1, self.post2)
        self.assertEqual(set(self.ann.authored_posts.all()), {self.post1, self.post2})

    def test_reverse_add_rejects_unsaved_objects(self):
        with self.assertRaisesMessage(ValueError, "saved model instances"):
            self.ann.authored_posts.add(BlogPost())

    def test_reverse_add_accepts_content_object_and_stores_grouper(self):
        post1_content = BlogPostContent.admin_manager.filter(post=self.post1).first()
        self.ann.authored_posts.add(post1_content)  # pass content, not grouper
        self.assertEqual(set(self.ann.authored_posts.all()), {self.post1})

    def test_reverse_remove(self):
        self.ann.authored_posts.add(self.post1, self.post2)
        self.ann.authored_posts.remove(self.post1)
        self.assertEqual(set(self.ann.authored_posts.all()), {self.post2})

    def test_reverse_clear(self):
        self.ann.authored_posts.add(self.post1, self.post2)
        self.ann.authored_posts.clear()
        self.assertFalse(self.ann.authored_posts.exists())


class CascadeTests(RelationTestBase):
    def test_deleting_source_cascades_natively(self):
        post = self._post()
        ann = self._person("Ann", "ann")
        post.authors.add(ann)
        from djangocms_custom_content.contrib.blog.models import BlogPost as _BP

        through = _BP.authors.field.through
        post.delete()
        self.assertEqual(through.objects.count(), 0)

    def test_deleting_target_cascades_via_signal(self):
        post = self._post()
        ann = self._person("Ann", "ann")
        post.authors.add(ann)
        through = BlogPost.authors.field.through
        ann.delete()
        self.assertEqual(through.objects.count(), 0)


class CategoriesRelationTests(RelationTestBase):
    """The migrated ``BlogPost.categories`` relation: unordered, and targeting a
    grouperless content model (FlatCategory), exercising the fallback path."""

    def setUp(self):
        self.post = self._post()
        self.news = FlatCategory.objects.create(title="News", slug="news")
        self.tech = FlatCategory.objects.create(title="Tech", slug="tech")

    def test_forward_and_reverse(self):
        self.post.categories.add(self.news, self.tech)
        self.assertEqual(set(self.post.categories.all()), {self.news, self.tech})
        # reverse accessor invited onto FlatCategory
        self.assertEqual(set(self.news.blog_posts.all()), {self.post})

    def test_target_is_the_content_model_when_no_grouper(self):
        # FlatCategory has no grouper, so the relation targets FlatCategory itself.
        self.assertIs(grouper_model_of(FlatCategory), FlatCategory)

    def test_reorder_requires_ordered_relation(self):
        # ``categories`` is unordered, so reorder() must refuse rather than no-op.
        self.post.categories.add(self.news, self.tech)
        with self.assertRaises(TypeError):
            self.post.categories.reorder([self.tech, self.news])


class VersionCopySurvivalTests(RelationTestBase):
    """The headline guarantee: relations are anchored to the grouper, so a new
    content version (a new content row with a new pk) keeps the relation."""

    def test_relation_survives_new_content_version(self):
        post = self._post(title="v1")
        ann = self._person("Ann", "ann")
        post.authors.add(ann)

        # Simulate a version copy: a brand-new content row for the same grouper,
        # with a different pk. Anchoring to the grouper means authors are intact.
        new_content = BlogPostContent.objects.with_user(self.user).create(
            post=post, title="v2", slug="a-post", excerpt="", body="", language="en"
        )
        self.assertNotEqual(new_content.pk, post.pk)  # new content row, same grouper
        self.assertEqual(set(post.authors.all()), {ann})
        # And the reverse direction still resolves the grouper, not a content pk.
        self.assertEqual(set(ann.authored_posts.all()), {post})
