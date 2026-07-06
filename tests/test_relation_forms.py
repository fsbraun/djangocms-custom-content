"""The relation fields live at the ModelForm layer and work without the admin."""

from unittest.mock import patch

import pytest
from django import forms
from django.contrib.auth import get_user_model
from django.test import TestCase

from djangocms_custom_content.contrib.blog.models import BlogPost, BlogPostContent
from djangocms_custom_content.contrib.categories.models import FlatCategory
from djangocms_custom_content.contrib.people.models import Person, PersonContent
from djangocms_custom_content.forms import RelationModelForm
from djangocms_custom_content.relations import RelationManager

User = get_user_model()
pytestmark = pytest.mark.django_db


class BlogPostRelationForm(RelationModelForm):
    """A plain ModelForm — no admin involved — for the BlogPost grouper."""

    class Meta:
        model = BlogPost
        fields = []  # BlogPost has no editable own fields; relations are added by the metaclass


class RelationModelFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser("admin", "admin@example.com", "pw")

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

    def _category(self, title, slug):
        return FlatCategory.objects.create(title=title, slug=slug)

    def test_relation_fields_declared_on_form(self):
        self.assertIn("authors", BlogPostRelationForm.base_fields)
        self.assertIn("categories", BlogPostRelationForm.base_fields)
        # ordered relation -> order-preserving field
        from djangocms_custom_content.forms import OrderedModelMultipleChoiceField

        self.assertIsInstance(BlogPostRelationForm.base_fields["authors"], OrderedModelMultipleChoiceField)
        self.assertIsInstance(BlogPostRelationForm.base_fields["categories"], forms.ModelMultipleChoiceField)

    def test_initial_loaded_from_instance(self):
        post = self._post()
        ann, bob = self._person("Ann", "ann"), self._person("Bob", "bob")
        post.authors.add(bob, ann)
        form = BlogPostRelationForm(instance=post)
        self.assertEqual(list(form.initial["authors"]), [bob.pk, ann.pk])

    def test_save_persists_relations(self):
        post = self._post()
        ann, bob = self._person("Ann", "ann"), self._person("Bob", "bob")
        form = BlogPostRelationForm(data={"authors": [str(bob.pk), str(ann.pk)], "categories": []}, instance=post)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        # ordered relation keeps the submitted order
        self.assertEqual(list(post.authors.all()), [bob, ann])

    def test_save_commit_false_defers_to_save_m2m(self):
        post = self._post()
        ann = self._person("Ann", "ann")
        form = BlogPostRelationForm(data={"authors": [str(ann.pk)], "categories": []}, instance=post)
        self.assertTrue(form.is_valid(), form.errors)
        form.save(commit=False)
        self.assertEqual(post.authors.count(), 0)  # not yet persisted
        form.save_m2m()
        self.assertEqual(set(post.authors.all()), {ann})

    def test_save_skips_unchanged_relations(self):
        post = self._post()
        ann, bob = self._person("Ann", "ann"), self._person("Bob", "bob")
        post.authors.add(bob, ann)

        form = BlogPostRelationForm(data={"authors": [str(bob.pk), str(ann.pk)], "categories": []}, instance=post)
        self.assertTrue(form.is_valid(), form.errors)
        with patch.object(RelationManager, "set") as set_relation:
            form.save()

        set_relation.assert_not_called()

    def test_save_compares_unordered_relations_as_sets(self):
        post = self._post()
        alpha = self._category("Alpha", "alpha")
        zulu = self._category("Zulu", "zulu")
        post.categories.add(alpha, zulu)

        form = BlogPostRelationForm(data={"authors": [], "categories": [str(zulu.pk), str(alpha.pk)]}, instance=post)
        self.assertTrue(form.is_valid(), form.errors)
        form.cleaned_data["categories"] = [zulu, alpha]

        with patch.object(RelationManager, "set") as set_relation:
            form.save()

        set_relation.assert_not_called()
