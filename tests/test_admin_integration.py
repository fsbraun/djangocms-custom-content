"""
Tests for GenericM2M admin integration (forms, filters, mixins).
"""

import pytest
from django import forms
from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory, TestCase

from djangocms_custom_content.admin import GenericM2MAdminMixin, GenericM2MListFilter
from djangocms_custom_content.forms import GenericM2MFormField, GenericM2MModelForm
from tests.test_app.models import Author, AuthorRelation, Book, BookRelation

User = get_user_model()
pytestmark = pytest.mark.django_db


class GenericM2MFormFieldTestCase(TestCase):
    """Test case for GenericM2MFormField."""

    def setUp(self):
        """Set up test fixtures."""
        self.author1 = Author.objects.create(name="Author 1")
        self.author2 = Author.objects.create(name="Author 2")
        self.author3 = Author.objects.create(name="Author 3")
        self.book = Book.objects.create(title="Test Book", author="Test")

    def test_field_initialization(self):
        """Test that GenericM2MFormField initializes correctly."""
        field = GenericM2MFormField(
            instance=self.book,
            through_model=AuthorRelation,
            related_field_name="instance",
            label="Authors",
            required=False,
        )

        self.assertEqual(field.instance, self.book)
        self.assertEqual(field.through_model, AuthorRelation)
        self.assertEqual(field.related_field_name, "instance")
        self.assertIsNotNone(field.queryset)

    def test_prepare_value_empty(self):
        """Test prepare_value with no existing relations."""
        field = GenericM2MFormField(
            instance=self.book,
            through_model=AuthorRelation,
            related_field_name="instance",
        )

        value = field.prepare_value(None)
        self.assertEqual(value, [])

    def test_prepare_value_with_relations(self):
        """Test prepare_value with existing relations."""
        # Create relations
        ct = ContentType.objects.get_for_model(self.book)
        AuthorRelation.objects.create(instance=self.author1, content_type=ct, object_id=self.book.pk)
        AuthorRelation.objects.create(instance=self.author2, content_type=ct, object_id=self.book.pk)

        field = GenericM2MFormField(
            instance=self.book,
            through_model=AuthorRelation,
            related_field_name="instance",
        )

        value = field.prepare_value(None)
        self.assertEqual(len(value), 2)
        self.assertIn(self.author1.pk, value)
        self.assertIn(self.author2.pk, value)

    def test_clean_valid_data(self):
        """Test clean method with valid data."""
        field = GenericM2MFormField(
            instance=self.book,
            through_model=AuthorRelation,
            related_field_name="instance",
            required=False,
        )

        cleaned = field.clean([self.author1.pk, self.author2.pk])
        # clean() returns a queryset, so we need to evaluate it
        self.assertEqual(cleaned.count(), 2)

    def test_clean_required_empty(self):
        """Test clean method with required field and empty value."""
        field = GenericM2MFormField(
            instance=self.book,
            through_model=AuthorRelation,
            related_field_name="instance",
            required=True,
        )

        with self.assertRaises(forms.ValidationError):
            field.clean([])

    def test_save_relations_add_new(self):
        """Test save_relations adding new relations."""
        field = GenericM2MFormField(
            instance=self.book,
            through_model=AuthorRelation,
            related_field_name="instance",
        )
        cleaned_data = [self.author1, self.author2]

        field.save_relations(self.book, cleaned_data)

        ct = ContentType.objects.get_for_model(self.book)
        relations = AuthorRelation.objects.filter(content_type=ct, object_id=self.book.pk)
        self.assertEqual(relations.count(), 2)

    def test_save_relations_remove_existing(self):
        """Test save_relations removing existing relations."""
        ct = ContentType.objects.get_for_model(self.book)
        AuthorRelation.objects.create(instance=self.author1, content_type=ct, object_id=self.book.pk)
        AuthorRelation.objects.create(instance=self.author2, content_type=ct, object_id=self.book.pk)

        field = GenericM2MFormField(
            instance=self.book,
            through_model=AuthorRelation,
            related_field_name="instance",
        )
        cleaned_data = [self.author1]  # Only keep author1

        field.save_relations(self.book, cleaned_data)

        relations = AuthorRelation.objects.filter(content_type=ct, object_id=self.book.pk)
        self.assertEqual(relations.count(), 1)
        self.assertEqual(relations.first().instance, self.author1)

    def test_save_relations_update(self):
        """Test save_relations updating relations."""
        ct = ContentType.objects.get_for_model(self.book)
        AuthorRelation.objects.create(instance=self.author1, content_type=ct, object_id=self.book.pk)

        field = GenericM2MFormField(
            instance=self.book,
            through_model=AuthorRelation,
            related_field_name="instance",
        )
        cleaned_data = [self.author2, self.author3]  # Replace with different authors

        field.save_relations(self.book, cleaned_data)

        relations = AuthorRelation.objects.filter(content_type=ct, object_id=self.book.pk)
        self.assertEqual(relations.count(), 2)
        pks = [r.instance.pk for r in relations]
        self.assertIn(self.author2.pk, pks)
        self.assertIn(self.author3.pk, pks)
        self.assertNotIn(self.author1.pk, pks)


class GenericM2MModelFormTestCase(TestCase):
    """Test case for GenericM2MModelForm."""

    def setUp(self):
        """Set up test fixtures."""
        self.author1 = Author.objects.create(name="Author 1")
        self.author2 = Author.objects.create(name="Author 2")
        self.book = Book.objects.create(title="Test Book", author="Test")

    def test_form_initialization(self):
        """Test that GenericM2MModelForm initializes and creates fields."""

        class TestBookForm(GenericM2MModelForm):
            class Meta:
                model = Book
                fields = ["title", "author"]
                generic_m2m_fields = {
                    "authors": {
                        "through_model": AuthorRelation,
                        "related_field_name": "instance",
                        "label": "Authors",
                        "required": False,
                    }
                }

        form = TestBookForm(instance=self.book)

        # Check that the generic M2M field was added
        self.assertIn("authors", form.fields)
        self.assertIsInstance(form.fields["authors"], GenericM2MFormField)
        self.assertEqual(form.fields["authors"].label, "Authors")

    def test_form_save_with_m2m(self):
        """Test that form saves M2M relations correctly."""

        class TestBookForm(GenericM2MModelForm):
            class Meta:
                model = Book
                fields = ["title", "author"]
                generic_m2m_fields = {
                    "authors": {
                        "through_model": AuthorRelation,
                        "related_field_name": "instance",
                        "label": "Authors",
                        "required": False,
                    }
                }

        # Create form with data
        form = TestBookForm(
            data={
                "title": "Updated Book",
                "author": "Test Author",
                "authors": [self.author1.pk, self.author2.pk],
            },
            instance=self.book,
        )

        self.assertTrue(form.is_valid(), form.errors)
        instance = form.save()

        # Check that the book was updated
        self.assertEqual(instance.title, "Updated Book")

        # Check that relations were created
        ct = ContentType.objects.get_for_model(self.book)
        relations = AuthorRelation.objects.filter(content_type=ct, object_id=self.book.pk)
        self.assertEqual(relations.count(), 2)

    def test_form_with_custom_widget(self):
        """Test that custom widgets can be specified."""

        class TestBookForm(GenericM2MModelForm):
            class Meta:
                model = Book
                fields = ["title", "author"]
                generic_m2m_fields = {
                    "authors": {
                        "through_model": AuthorRelation,
                        "related_field_name": "instance",
                        "label": "Authors",
                        "required": False,
                        "widget": forms.CheckboxSelectMultiple,
                    }
                }

        form = TestBookForm(instance=self.book)
        self.assertIsInstance(form.fields["authors"].widget, forms.CheckboxSelectMultiple)


class GenericM2MAdminMixinTestCase(TestCase):
    """Test case for GenericM2MAdminMixin."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.superuser = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="password"
        )
        self.author1 = Author.objects.create(name="Author 1")
        self.book1 = Book.objects.create(title="Book 1", author="Test")
        self.book2 = Book.objects.create(title="Book 2", author="Test")

        # Create relations
        ct = ContentType.objects.get_for_model(self.book1)
        AuthorRelation.objects.create(instance=self.author1, content_type=ct, object_id=self.book1.pk)

    def test_mixin_get_queryset(self):
        """Test that mixin's get_queryset works."""

        class TestBookAdmin(GenericM2MAdminMixin, admin.ModelAdmin):
            generic_m2m_fields = ["authors"]

        site = AdminSite()
        book_admin = TestBookAdmin(Book, site)
        request = self.factory.get("/admin/test_app/book/")
        request.user = self.superuser

        # Note: The descriptor must be set on the model for this to work
        # Since Book doesn't have 'authors' descriptor in test models, this test
        # just verifies the method doesn't crash
        queryset = book_admin.get_queryset(request)
        self.assertIsNotNone(queryset)


class GenericM2MListFilterTestCase(TestCase):
    """Test case for GenericM2MListFilter."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.superuser = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="password"
        )
        self.author1 = Author.objects.create(name="Author 1")
        self.author2 = Author.objects.create(name="Author 2")
        self.book1 = Book.objects.create(title="Book 1", author="Test")
        self.book2 = Book.objects.create(title="Book 2", author="Test")
        self.book3 = Book.objects.create(title="Book 3", author="Test")

        # Create relations
        ct = ContentType.objects.get_for_model(self.book1)
        AuthorRelation.objects.create(instance=self.author1, content_type=ct, object_id=self.book1.pk)
        ct = ContentType.objects.get_for_model(self.book2)
        AuthorRelation.objects.create(instance=self.author1, content_type=ct, object_id=self.book2.pk)
        ct = ContentType.objects.get_for_model(self.book3)
        AuthorRelation.objects.create(instance=self.author2, content_type=ct, object_id=self.book3.pk)

    def test_filter_lookups(self):
        """Test that filter returns correct lookups."""

        class TestAuthorFilter(GenericM2MListFilter):
            title = "Author"
            parameter_name = "author"
            relation_model = AuthorRelation
            related_field = "instance"

        site = AdminSite()
        book_admin = admin.ModelAdmin(Book, site)
        request = self.factory.get("/admin/test_app/book/")
        request.user = self.superuser

        filter_instance = TestAuthorFilter(request, {}, Book, book_admin)
        lookups = filter_instance.lookups(request, book_admin)

        self.assertEqual(len(lookups), 2)
        lookup_ids = [lookup[0] for lookup in lookups]
        self.assertIn(self.author1.pk, lookup_ids)
        self.assertIn(self.author2.pk, lookup_ids)

    def test_filter_queryset_with_selection(self):
        """Test that filter correctly filters queryset."""

        class TestAuthorFilter(GenericM2MListFilter):
            title = "Author"
            parameter_name = "author"
            relation_model = AuthorRelation
            related_field = "instance"

        site = AdminSite()
        book_admin = admin.ModelAdmin(Book, site)
        request = self.factory.get(f"/admin/test_app/book/?author={self.author1.pk}")
        request.user = self.superuser

        filter_instance = TestAuthorFilter(request, {"author": str(self.author1.pk)}, Book, book_admin)
        queryset = Book.objects.all()
        filtered = filter_instance.queryset(request, queryset)

        self.assertEqual(filtered.count(), 2)
        self.assertIn(self.book1, filtered)
        self.assertIn(self.book2, filtered)
        self.assertNotIn(self.book3, filtered)

    def test_filter_queryset_no_selection(self):
        """Test that filter returns unfiltered queryset when no selection."""

        class TestAuthorFilter(GenericM2MListFilter):
            title = "Author"
            parameter_name = "author"
            relation_model = AuthorRelation
            related_field = "instance"

        site = AdminSite()
        book_admin = admin.ModelAdmin(Book, site)
        request = self.factory.get("/admin/test_app/book/")
        request.user = self.superuser

        filter_instance = TestAuthorFilter(request, {}, Book, book_admin)
        queryset = Book.objects.all()
        filtered = filter_instance.queryset(request, queryset)

        self.assertEqual(filtered.count(), 3)
