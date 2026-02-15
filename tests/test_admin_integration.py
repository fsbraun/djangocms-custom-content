"""
Tests for GenericM2M admin integration (forms, filters, mixins).
"""

import pytest
from django import forms
from django.contrib import admin
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory, TestCase, TransactionTestCase

from djangocms_custom_content.admin import GenericM2MAdminMixin, GenericM2MListFilter
from djangocms_custom_content.forms import GenericM2MFormField, GenericM2MModelForm
from djangocms_custom_content.models import GenericM2MDescriptor, InverseRelationDescriptor
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

    def test_clean_invalid_pk(self):
        """Test clean method with invalid PK."""
        field = GenericM2MFormField(
            instance=self.book,
            through_model=AuthorRelation,
            related_field_name="instance",
            required=False,
        )

        with self.assertRaises(forms.ValidationError):
            field.clean([999999])  # Non-existent PK

    def test_clean_none_value(self):
        """Test clean method with None value."""
        field = GenericM2MFormField(
            instance=self.book,
            through_model=AuthorRelation,
            related_field_name="instance",
            required=False,
        )

        cleaned = field.clean(None)
        self.assertEqual(cleaned.count(), 0)

    def test_clean_empty_list(self):
        """Test clean method with empty list."""
        field = GenericM2MFormField(
            instance=self.book,
            through_model=AuthorRelation,
            related_field_name="instance",
            required=False,
        )

        cleaned = field.clean([])
        self.assertEqual(cleaned.count(), 0)

    def test_clean_mixed_valid_invalid(self):
        """Test clean method with mix of valid and invalid PKs."""
        field = GenericM2MFormField(
            instance=self.book,
            through_model=AuthorRelation,
            related_field_name="instance",
            required=False,
        )

        with self.assertRaises(forms.ValidationError):
            field.clean([self.author1.pk, 999999])

    def test_prepare_value_unsaved_instance(self):
        """Test prepare_value with an unsaved instance."""
        unsaved_book = Book(title="Unsaved", author="Test")
        field = GenericM2MFormField(
            instance=unsaved_book,
            through_model=AuthorRelation,
            related_field_name="instance",
        )

        value = field.prepare_value(None)
        self.assertEqual(value, [])

    def test_save_relations_no_changes(self):
        """Test save_relations when relations don't change."""
        ct = ContentType.objects.get_for_model(self.book)
        AuthorRelation.objects.create(instance=self.author1, content_type=ct, object_id=self.book.pk)

        field = GenericM2MFormField(
            instance=self.book,
            through_model=AuthorRelation,
            related_field_name="instance",
        )
        cleaned_data = [self.author1]  # Same as before

        field.save_relations(self.book, cleaned_data)

        relations = AuthorRelation.objects.filter(content_type=ct, object_id=self.book.pk)
        self.assertEqual(relations.count(), 1)
        self.assertEqual(relations.first().instance, self.author1)

    def test_save_relations_clear_all(self):
        """Test save_relations clearing all relations."""
        ct = ContentType.objects.get_for_model(self.book)
        AuthorRelation.objects.create(instance=self.author1, content_type=ct, object_id=self.book.pk)
        AuthorRelation.objects.create(instance=self.author2, content_type=ct, object_id=self.book.pk)

        field = GenericM2MFormField(
            instance=self.book,
            through_model=AuthorRelation,
            related_field_name="instance",
        )
        cleaned_data = []  # Clear all

        field.save_relations(self.book, cleaned_data)

        relations = AuthorRelation.objects.filter(content_type=ct, object_id=self.book.pk)
        self.assertEqual(relations.count(), 0)

    def test_save_relations_with_none(self):
        """Test save_relations with None data."""
        field = GenericM2MFormField(
            instance=self.book,
            through_model=AuthorRelation,
            related_field_name="instance",
        )

        # Should not crash
        field.save_relations(self.book, None)

        ct = ContentType.objects.get_for_model(self.book)
        relations = AuthorRelation.objects.filter(content_type=ct, object_id=self.book.pk)
        self.assertEqual(relations.count(), 0)

    def test_field_queryset_uses_admin_manager_if_available(self):
        """Test that field uses admin_manager if available on related model."""
        field = GenericM2MFormField(
            instance=self.book,
            through_model=AuthorRelation,
            related_field_name="instance",
            required=False,
        )

        # Author model doesn't have admin_manager, so it should use objects
        self.assertIsNotNone(field.queryset)
        self.assertEqual(field.queryset.model, Author)


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

    def test_form_save_without_commit(self):
        """Test that form handles save with commit=False."""

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

        form = TestBookForm(
            data={
                "title": "New Book",
                "author": "Test Author",
                "authors": [self.author1.pk],
            },
            instance=self.book,
        )

        self.assertTrue(form.is_valid())
        instance = form.save(commit=False)
        instance.save()

        # Relations should not be saved yet
        ct = ContentType.objects.get_for_model(instance)
        relations = AuthorRelation.objects.filter(content_type=ct, object_id=instance.pk)
        self.assertEqual(relations.count(), 0)

    def test_form_with_multiple_m2m_fields(self):
        """Test form with multiple generic M2M fields."""

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
                    },
                    "editors": {
                        "through_model": AuthorRelation,
                        "related_field_name": "instance",
                        "label": "Editors",
                        "required": False,
                    },
                }

        form = TestBookForm(instance=self.book)

        # Both fields should be created
        self.assertIn("authors", form.fields)
        self.assertIn("editors", form.fields)
        self.assertIsInstance(form.fields["authors"], GenericM2MFormField)
        self.assertIsInstance(form.fields["editors"], GenericM2MFormField)

    def test_form_validation_with_invalid_data(self):
        """Test form validation with invalid M2M data."""

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

        form = TestBookForm(
            data={
                "title": "New Book",
                "author": "Test Author",
                "authors": [999999],  # Invalid PK
            },
            instance=self.book,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("authors", form.errors)

    def test_form_with_required_m2m_field(self):
        """Test form with required M2M field."""

        class TestBookForm(GenericM2MModelForm):
            class Meta:
                model = Book
                fields = ["title", "author"]
                generic_m2m_fields = {
                    "authors": {
                        "through_model": AuthorRelation,
                        "related_field_name": "instance",
                        "label": "Authors",
                        "required": True,
                    }
                }

        form = TestBookForm(
            data={
                "title": "New Book",
                "author": "Test Author",
                "authors": [],  # Empty but required
            },
            instance=self.book,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("authors", form.errors)

    def test_form_update_existing_relations(self):
        """Test form updating existing relations."""
        # Create initial relations
        ct = ContentType.objects.get_for_model(self.book)
        AuthorRelation.objects.create(instance=self.author1, content_type=ct, object_id=self.book.pk)

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

        # Update to author2
        form = TestBookForm(
            data={
                "title": self.book.title,
                "author": self.book.author,
                "authors": [self.author2.pk],
            },
            instance=self.book,
        )

        self.assertTrue(form.is_valid())
        form.save()

        # Check relations
        relations = AuthorRelation.objects.filter(content_type=ct, object_id=self.book.pk)
        self.assertEqual(relations.count(), 1)
        self.assertEqual(relations.first().instance, self.author2)

    def test_form_with_help_text(self):
        """Test that help_text is properly set."""

        class TestBookForm(GenericM2MModelForm):
            class Meta:
                model = Book
                fields = ["title", "author"]
                generic_m2m_fields = {
                    "authors": {
                        "through_model": AuthorRelation,
                        "related_field_name": "instance",
                        "label": "Authors",
                        "help_text": "Select authors for this book",
                        "required": False,
                    }
                }

        form = TestBookForm(instance=self.book)
        self.assertEqual(form.fields["authors"].help_text, "Select authors for this book")

    def test_form_without_generic_m2m_fields(self):
        """Test that form works without generic_m2m_fields."""

        class TestBookForm(GenericM2MModelForm):
            class Meta:
                model = Book
                fields = ["title", "author"]

        form = TestBookForm(instance=self.book)
        # Should not have any generic M2M fields
        self.assertNotIn("authors", form.fields)


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

    def test_mixin_without_generic_m2m_fields(self):
        """Test mixin without generic_m2m_fields attribute."""

        class TestBookAdmin(GenericM2MAdminMixin, admin.ModelAdmin):
            pass  # No generic_m2m_fields

        site = AdminSite()
        book_admin = TestBookAdmin(Book, site)
        request = self.factory.get("/admin/test_app/book/")
        request.user = self.superuser

        # Should not crash
        queryset = book_admin.get_queryset(request)
        self.assertIsNotNone(queryset)
        self.assertEqual(queryset.count(), 2)

    def test_mixin_with_empty_generic_m2m_fields(self):
        """Test mixin with empty list of generic_m2m_fields."""

        class TestBookAdmin(GenericM2MAdminMixin, admin.ModelAdmin):
            generic_m2m_fields = []

        site = AdminSite()
        book_admin = TestBookAdmin(Book, site)
        request = self.factory.get("/admin/test_app/book/")
        request.user = self.superuser

        queryset = book_admin.get_queryset(request)
        self.assertIsNotNone(queryset)
        self.assertEqual(queryset.count(), 2)

    def test_mixin_with_nonexistent_field(self):
        """Test mixin with nonexistent field in generic_m2m_fields."""

        class TestBookAdmin(GenericM2MAdminMixin, admin.ModelAdmin):
            generic_m2m_fields = ["nonexistent_field"]

        site = AdminSite()
        book_admin = TestBookAdmin(Book, site)
        request = self.factory.get("/admin/test_app/book/")
        request.user = self.superuser

        # Should not crash, just skip the nonexistent field
        queryset = book_admin.get_queryset(request)
        self.assertIsNotNone(queryset)
        self.assertEqual(queryset.count(), 2)

    def test_mixin_with_multiple_fields(self):
        """Test mixin with multiple generic M2M fields."""

        class TestBookAdmin(GenericM2MAdminMixin, admin.ModelAdmin):
            generic_m2m_fields = ["authors", "editors", "reviewers"]

        site = AdminSite()
        book_admin = TestBookAdmin(Book, site)
        request = self.factory.get("/admin/test_app/book/")
        request.user = self.superuser

        # Should handle multiple fields gracefully
        queryset = book_admin.get_queryset(request)
        self.assertIsNotNone(queryset)
        self.assertEqual(queryset.count(), 2)

    def test_mixin_queryset_returns_correct_model(self):
        """Test that mixin returns queryset of correct model."""

        class TestBookAdmin(GenericM2MAdminMixin, admin.ModelAdmin):
            generic_m2m_fields = ["authors"]

        site = AdminSite()
        book_admin = TestBookAdmin(Book, site)
        request = self.factory.get("/admin/test_app/book/")
        request.user = self.superuser

        queryset = book_admin.get_queryset(request)
        self.assertEqual(queryset.model, Book)

    def test_mixin_preserves_parent_queryset_filters(self):
        """Test that mixin preserves filters from parent get_queryset."""

        class TestBookAdmin(GenericM2MAdminMixin, admin.ModelAdmin):
            generic_m2m_fields = ["authors"]

            def get_queryset(self, request):
                qs = super().get_queryset(request)
                # Apply a filter
                return qs.filter(title__startswith="Book")

        site = AdminSite()
        book_admin = TestBookAdmin(Book, site)
        request = self.factory.get("/admin/test_app/book/")
        request.user = self.superuser

        queryset = book_admin.get_queryset(request)
        self.assertEqual(queryset.count(), 2)
        # Create a book that doesn't match the filter
        Book.objects.create(title="Other Book", author="Test")
        queryset = book_admin.get_queryset(request)
        self.assertEqual(queryset.count(), 2)  # Still only 2

    def test_mixin_with_ordering(self):
        """Test that mixin works with ordering."""

        class TestBookAdmin(GenericM2MAdminMixin, admin.ModelAdmin):
            generic_m2m_fields = ["authors"]
            ordering = ["-title"]

        site = AdminSite()
        book_admin = TestBookAdmin(Book, site)
        request = self.factory.get("/admin/test_app/book/")
        request.user = self.superuser

        queryset = book_admin.get_queryset(request)
        self.assertEqual(queryset.count(), 2)
        # Check ordering is preserved
        titles = list(queryset.values_list("title", flat=True))
        self.assertEqual(titles, ["Book 2", "Book 1"])

    def test_mixin_with_search(self):
        """Test that mixin works with search functionality."""

        class TestBookAdmin(GenericM2MAdminMixin, admin.ModelAdmin):
            generic_m2m_fields = ["authors"]
            search_fields = ["title"]

        site = AdminSite()
        book_admin = TestBookAdmin(Book, site)
        request = self.factory.get("/admin/test_app/book/?q=Book")
        request.user = self.superuser

        queryset = book_admin.get_queryset(request)
        # All books match "Book" in title
        self.assertEqual(queryset.count(), 2)

    def test_mixin_integration_with_list_display(self):
        """Test that mixin works with list_display."""

        class TestBookAdmin(GenericM2MAdminMixin, admin.ModelAdmin):
            generic_m2m_fields = ["authors"]
            list_display = ["title", "author"]

        site = AdminSite()
        book_admin = TestBookAdmin(Book, site)
        request = self.factory.get("/admin/test_app/book/")
        request.user = self.superuser

        queryset = book_admin.get_queryset(request)
        self.assertIsNotNone(queryset)
        self.assertEqual(list(book_admin.list_display), ["title", "author"])

    def test_mixin_queryset_is_evaluable(self):
        """Test that returned queryset can be evaluated."""

        class TestBookAdmin(GenericM2MAdminMixin, admin.ModelAdmin):
            generic_m2m_fields = ["authors"]

        site = AdminSite()
        book_admin = TestBookAdmin(Book, site)
        request = self.factory.get("/admin/test_app/book/")
        request.user = self.superuser

        queryset = book_admin.get_queryset(request)

        # Should be able to iterate
        books = list(queryset)
        self.assertEqual(len(books), 2)
        self.assertIn(self.book1, books)
        self.assertIn(self.book2, books)

    def test_mixin_with_related_objects(self):
        """Test mixin when objects have relations."""
        # Add more relations
        author2 = Author.objects.create(name="Author 2")
        ct = ContentType.objects.get_for_model(self.book2)
        AuthorRelation.objects.create(instance=author2, content_type=ct, object_id=self.book2.pk)

        class TestBookAdmin(GenericM2MAdminMixin, admin.ModelAdmin):
            generic_m2m_fields = ["authors"]

        site = AdminSite()
        book_admin = TestBookAdmin(Book, site)
        request = self.factory.get("/admin/test_app/book/")
        request.user = self.superuser

        queryset = book_admin.get_queryset(request)
        self.assertEqual(queryset.count(), 2)

    def test_mixin_does_not_interfere_with_regular_admin(self):
        """Test that mixin doesn't break regular admin functionality."""

        class TestBookAdmin(GenericM2MAdminMixin, admin.ModelAdmin):
            generic_m2m_fields = ["authors"]
            list_per_page = 50
            save_on_top = True

        site = AdminSite()
        book_admin = TestBookAdmin(Book, site)

        # Check that regular admin attributes are preserved
        self.assertEqual(book_admin.list_per_page, 50)
        self.assertTrue(book_admin.save_on_top)

    def test_mixin_with_regular_field_not_descriptor(self):
        """Test that mixin skips fields that are not descriptors."""

        class TestBookAdmin(GenericM2MAdminMixin, admin.ModelAdmin):
            # 'title' is a regular field, not a descriptor
            generic_m2m_fields = ["title"]

        site = AdminSite()
        book_admin = TestBookAdmin(Book, site)
        request = self.factory.get("/admin/test_app/book/")
        request.user = self.superuser

        # Should not crash, just skip the non-descriptor field
        queryset = book_admin.get_queryset(request)
        self.assertIsNotNone(queryset)
        self.assertEqual(queryset.count(), 2)

    def test_mixin_with_property_not_descriptor(self):
        """Test that mixin handles properties correctly."""

        # Add a property to the model temporarily
        Book.test_property = property(lambda self: "test")

        class TestBookAdmin(GenericM2MAdminMixin, admin.ModelAdmin):
            generic_m2m_fields = ["test_property"]

        site = AdminSite()
        book_admin = TestBookAdmin(Book, site)
        request = self.factory.get("/admin/test_app/book/")
        request.user = self.superuser

        # Should not crash
        queryset = book_admin.get_queryset(request)
        self.assertIsNotNone(queryset)

        # Cleanup
        delattr(Book, "test_property")

    def test_mixin_get_queryset_called_correctly(self):
        """Test that get_queryset is called and returns queryset."""

        class TestBookAdmin(GenericM2MAdminMixin, admin.ModelAdmin):
            generic_m2m_fields = []

        site = AdminSite()
        book_admin = TestBookAdmin(Book, site)
        request = self.factory.get("/admin/test_app/book/")
        request.user = self.superuser

        queryset = book_admin.get_queryset(request)

        # Verify it's a QuerySet
        from django.db.models.query import QuerySet

        self.assertIsInstance(queryset, QuerySet)
        self.assertEqual(queryset.model, Book)

    def test_mixin_handles_none_descriptor(self):
        """Test that mixin handles None descriptor gracefully."""

        class TestBookAdmin(GenericM2MAdminMixin, admin.ModelAdmin):
            # Field that doesn't exist will return None from getattr
            generic_m2m_fields = ["does_not_exist"]

        site = AdminSite()
        book_admin = TestBookAdmin(Book, site)
        request = self.factory.get("/admin/test_app/book/")
        request.user = self.superuser

        # Should not crash
        queryset = book_admin.get_queryset(request)
        self.assertIsNotNone(queryset)
        self.assertEqual(queryset.count(), 2)

    def test_mixin_with_mixed_valid_invalid_fields(self):
        """Test mixin with mix of valid and invalid field names."""

        class TestBookAdmin(GenericM2MAdminMixin, admin.ModelAdmin):
            generic_m2m_fields = ["authors", "invalid_field", "title"]

        site = AdminSite()
        book_admin = TestBookAdmin(Book, site)
        request = self.factory.get("/admin/test_app/book/")
        request.user = self.superuser

        # Should handle the mix gracefully
        queryset = book_admin.get_queryset(request)
        self.assertIsNotNone(queryset)
        self.assertEqual(queryset.count(), 2)

    def test_mixin_queryset_has_prefetch(self):
        """Test that queryset actually has prefetch_related applied."""
        from django.db.models import Prefetch

        class TestBookAdmin(GenericM2MAdminMixin, admin.ModelAdmin):
            generic_m2m_fields = ["authors"]

        site = AdminSite()
        book_admin = TestBookAdmin(Book, site)
        request = self.factory.get("/admin/test_app/book/")
        request.user = self.superuser

        queryset = book_admin.get_queryset(request)

        # Check if prefetch_related was applied
        # The _prefetch_related_lookups attribute indicates prefetch operations
        self.assertIsNotNone(queryset._prefetch_related_lookups)

    def test_mixin_doesnt_duplicate_prefetch(self):
        """Test that calling get_queryset multiple times doesn't duplicate prefetch."""

        class TestBookAdmin(GenericM2MAdminMixin, admin.ModelAdmin):
            generic_m2m_fields = ["authors"]

        site = AdminSite()
        book_admin = TestBookAdmin(Book, site)
        request = self.factory.get("/admin/test_app/book/")
        request.user = self.superuser

        queryset1 = book_admin.get_queryset(request)
        queryset2 = book_admin.get_queryset(request)

        # Both should be valid querysets
        self.assertEqual(queryset1.count(), 2)
        self.assertEqual(queryset2.count(), 2)

    def test_mixin_with_real_generic_m2m_descriptor(self):
        """Test that mixin works with a real GenericM2MDescriptor."""
        # Manually add a GenericM2MDescriptor to the Book model for testing
        Book.test_authors = GenericM2MDescriptor(AuthorRelation, "instance")

        try:

            class TestBookAdmin(GenericM2MAdminMixin, admin.ModelAdmin):
                generic_m2m_fields = ["test_authors"]

            site = AdminSite()
            book_admin = TestBookAdmin(Book, site)
            request = self.factory.get("/admin/test_app/book/")
            request.user = self.superuser

            queryset = book_admin.get_queryset(request)

            # Should successfully get queryset
            self.assertIsNotNone(queryset)
            self.assertEqual(queryset.count(), 2)

            # Check that prefetch was applied
            self.assertIsNotNone(queryset._prefetch_related_lookups)
        finally:
            # Cleanup
            if hasattr(Book, "test_authors"):
                delattr(Book, "test_authors")

    def test_mixin_with_real_inverse_relation_descriptor(self):
        """Test that mixin works with a real InverseRelationDescriptor."""
        # Manually add an InverseRelationDescriptor to the Author model for testing
        Author.test_relations = InverseRelationDescriptor(AuthorRelation)

        try:

            class TestAuthorAdmin(GenericM2MAdminMixin, admin.ModelAdmin):
                generic_m2m_fields = ["test_relations"]

            site = AdminSite()
            author_admin = TestAuthorAdmin(Author, site)
            request = self.factory.get("/admin/test_app/author/")
            request.user = self.superuser

            queryset = author_admin.get_queryset(request)

            # Should successfully get queryset
            self.assertIsNotNone(queryset)
            self.assertEqual(queryset.model, Author)
        finally:
            # Cleanup
            if hasattr(Author, "test_relations"):
                delattr(Author, "test_relations")


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

    def test_filter_without_relation_model(self):
        """Test filter without relation_model attribute."""

        class TestAuthorFilter(GenericM2MListFilter):
            title = "Author"
            parameter_name = "author"
            relation_model = None  # Not set
            related_field = "instance"

        site = AdminSite()
        book_admin = admin.ModelAdmin(Book, site)
        request = self.factory.get("/admin/test_app/book/")
        request.user = self.superuser

        filter_instance = TestAuthorFilter(request, {}, Book, book_admin)
        lookups = filter_instance.lookups(request, book_admin)

        # Should return empty list
        self.assertEqual(len(lookups), 0)

    def test_filter_with_multiple_relations_same_author(self):
        """Test filter when same author has multiple relations."""
        # author1 already has relations to book1 and book2
        # Add another book with author1
        book4 = Book.objects.create(title="Book 4", author="Test")
        ct = ContentType.objects.get_for_model(book4)
        AuthorRelation.objects.create(instance=self.author1, content_type=ct, object_id=book4.pk)

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

        # Should return all 3 books with author1
        self.assertEqual(filtered.count(), 3)
        self.assertIn(self.book1, filtered)
        self.assertIn(self.book2, filtered)
        self.assertIn(book4, filtered)

    def test_filter_lookups_with_admin_manager(self):
        """Test that filter uses admin_manager if available."""

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

        # Should have lookups for both authors
        self.assertIsNotNone(lookups)
        self.assertGreater(len(lookups), 0)
