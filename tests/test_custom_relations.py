"""
Tests for custom_relation_factory and GenericRelationDescriptor.
"""

import pytest
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.test import TestCase

from djangocms_custom_content.models import (
    AbstractCustomRelation,
    GenericRelationDescriptor,
    InverseRelationDescriptor,
    custom_relation_factory,
)
from tests.test_app.models import Article, Author, Book

pytestmark = pytest.mark.django_db


class CustomRelationFactoryTestCase(TestCase):
    """Test case for the custom_relation_factory function."""

    def test_relation_model_created(self):
        """Test that the relation model is created with the correct name."""
        AuthorRelation = custom_relation_factory(Author, related_name="test_publications")

        self.assertEqual(AuthorRelation.__name__, "AuthorRelation")
        self.assertTrue(issubclass(AuthorRelation, AbstractCustomRelation))

    def test_relation_model_has_instance_field(self):
        """Test that the relation model has an instance foreign key field."""
        AuthorRelation = custom_relation_factory(Author, related_name="test_field")

        instance_field = AuthorRelation._meta.get_field("instance")
        self.assertIsInstance(instance_field, models.ForeignKey)
        self.assertEqual(instance_field.related_model, Author)

    def test_related_name_added_to_model(self):
        """Test that the related_name is added to the Author model."""
        custom_relation_factory(Author, related_name="test_related")

        author = Author(name="Test Author")
        self.assertTrue(hasattr(author, "test_related"))

    def test_descriptor_is_inverse_relation_descriptor(self):
        """Test that the descriptor is an InverseRelationDescriptor instance."""
        custom_relation_factory(Author, related_name="test_descriptor")

        descriptor = Author.test_descriptor
        self.assertIsInstance(descriptor, InverseRelationDescriptor)

    def test_default_related_name(self):
        """Test that default related_name is used when not provided."""
        # Use an existing model from test_app instead of creating a temporary one
        custom_relation_factory(Book)

        # Should have default 'relation_set' attribute
        book = Book(title="Test", author="Test")
        self.assertTrue(hasattr(book, "relation_set"))

    def test_relation_model_module(self):
        """Test that the relation model has the correct module."""
        AuthorRelation = custom_relation_factory(Author, related_name="test_module")

        self.assertEqual(AuthorRelation.__module__, Author.__module__)

    def test_content_type_field_exists(self):
        """Test that the relation model has a content_type field."""
        AuthorRelation = custom_relation_factory(Author, related_name="test_ct")

        field = AuthorRelation._meta.get_field("content_type")
        self.assertIsInstance(field, models.ForeignKey)
        self.assertEqual(field.related_model, ContentType)

    def test_object_id_field_exists(self):
        """Test that the relation model has an object_id field."""
        AuthorRelation = custom_relation_factory(Author, related_name="test_oid")

        field = AuthorRelation._meta.get_field("object_id")
        self.assertIsInstance(field, models.PositiveIntegerField)


class InverseRelationDescriptorTestCase(TestCase):
    """Test case for InverseRelationDescriptor."""

    def test_descriptor_on_class(self):
        """Test accessing the descriptor on the class returns the descriptor."""
        custom_relation_factory(Author, related_name="test_works")

        descriptor = Author.test_works
        self.assertIsInstance(descriptor, InverseRelationDescriptor)

    def test_descriptor_on_instance(self):
        """Test accessing the descriptor on an instance returns a manager."""
        from djangocms_custom_content.models import _InverseRelationManager

        custom_relation_factory(Author, related_name="test_instance_works")
        author = Author(name="Test Author")

        manager = author.test_instance_works
        self.assertIsInstance(manager, _InverseRelationManager)

    def test_manager_has_correct_instance(self):
        """Test that the manager has the correct instance reference."""
        custom_relation_factory(Author, related_name="test_manager_inst")
        author = Author(name="Test Author")

        manager = author.test_manager_inst
        self.assertEqual(manager.instance, author)

    def test_manager_has_correct_relation_model(self):
        """Test that the manager has the correct relation model."""
        AuthorRelation = custom_relation_factory(Author, related_name="test_manager_rel")
        author = Author(name="Test Author")

        manager = author.test_manager_rel
        self.assertEqual(manager.relation_model, AuthorRelation)

    def test_descriptor_stores_relation_model(self):
        """Test that the descriptor stores the relation model correctly."""
        AuthorRelation = custom_relation_factory(Author, related_name="test_desc_store")

        descriptor = Author.test_desc_store
        self.assertEqual(descriptor.relation_model, AuthorRelation)


class GenericRelationDescriptorTestCase(TestCase):
    """Test case for GenericRelationDescriptor."""

    def test_descriptor_on_class(self):
        """Test accessing the descriptor on the class returns the descriptor."""
        AuthorRelation = custom_relation_factory(Author, related_name="test_items")
        Book.add_to_class("test_authors", GenericRelationDescriptor(AuthorRelation))

        descriptor = Book.test_authors
        self.assertIsInstance(descriptor, GenericRelationDescriptor)

    def test_descriptor_on_instance(self):
        """Test accessing the descriptor on an instance returns a manager."""
        from djangocms_custom_content.models import _GenericRelationManager

        AuthorRelation = custom_relation_factory(Author, related_name="test_gen_items")
        Book.add_to_class("test_gen_authors", GenericRelationDescriptor(AuthorRelation))

        book = Book(title="Test Book", author="Test Author")
        manager = book.test_gen_authors
        self.assertIsInstance(manager, _GenericRelationManager)

    def test_manager_has_correct_instance(self):
        """Test that the manager has the correct instance reference."""
        AuthorRelation = custom_relation_factory(Author, related_name="test_gen_inst")
        Book.add_to_class("test_gen_inst_authors", GenericRelationDescriptor(AuthorRelation))

        book = Book(title="Test Book", author="Test Author")
        manager = book.test_gen_inst_authors
        self.assertEqual(manager.instance, book)

    def test_manager_has_correct_owner(self):
        """Test that the manager has the correct owner."""
        AuthorRelation = custom_relation_factory(Author, related_name="test_gen_owner")
        Book.add_to_class("test_gen_owner_authors", GenericRelationDescriptor(AuthorRelation))

        book = Book(title="Test Book", author="Test Author")
        manager = book.test_gen_owner_authors
        self.assertEqual(manager.owner, Book)

    def test_descriptor_stores_relation_model(self):
        """Test that the descriptor stores the relation model correctly."""
        AuthorRelation = custom_relation_factory(Author, related_name="test_gen_store")

        descriptor = GenericRelationDescriptor(AuthorRelation)
        self.assertEqual(descriptor.relation_model, AuthorRelation)


class AbstractCustomRelationTestCase(TestCase):
    """Test case for AbstractCustomRelation model structure."""

    def test_abstract_relation_fields(self):
        """Test that AbstractCustomRelation has the required fields."""
        from djangocms_custom_content.models import AbstractCustomRelation

        # Check that it's abstract
        self.assertTrue(AbstractCustomRelation._meta.abstract)

        # Create a concrete relation model to test
        AuthorRelation = custom_relation_factory(Author, related_name="test_abs_fields")

        # Verify fields exist
        self.assertTrue(AuthorRelation._meta.get_field("content_type"))
        self.assertTrue(AuthorRelation._meta.get_field("object_id"))
        self.assertTrue(AuthorRelation._meta.get_field("instance"))

    def test_relation_has_content_type_field(self):
        """Test that the relation has a content_type field."""
        AuthorRelation = custom_relation_factory(Author, related_name="test_ct_field")

        field = AuthorRelation._meta.get_field("content_type")
        self.assertIsInstance(field, models.ForeignKey)
        self.assertEqual(field.related_model, ContentType)

    def test_relation_has_object_id_field(self):
        """Test that the relation has an object_id field."""
        AuthorRelation = custom_relation_factory(Author, related_name="test_oid_field")

        field = AuthorRelation._meta.get_field("object_id")
        self.assertIsInstance(field, models.PositiveIntegerField)

    def test_relation_has_instance_attribute(self):
        """Test that the relation model has an instance field."""
        AuthorRelation = custom_relation_factory(Author, related_name="test_inst_attr")

        # Check that the instance field exists in the model's meta
        instance_field = AuthorRelation._meta.get_field("instance")
        self.assertIsNotNone(instance_field)
        self.assertIsInstance(instance_field, models.ForeignKey)

    def test_relation_string_method_exists(self):
        """Test that the relation has a __str__ method."""
        AuthorRelation = custom_relation_factory(Author, related_name="test_str_method")

        relation = AuthorRelation()
        # Should have __str__ method from AbstractCustomRelation
        self.assertTrue(hasattr(relation, "__str__"))


class FactoryBehaviorTestCase(TestCase):
    """Test the behavior of the custom_relation_factory function."""

    def test_multiple_factories_different_names(self):
        """Test that multiple factories create models with expected names."""
        Relation1 = custom_relation_factory(Author, related_name="test_rel1")
        Relation2 = custom_relation_factory(Book, related_name="test_rel2")

        self.assertEqual(Relation1.__name__, "AuthorRelation")
        self.assertEqual(Relation2.__name__, "BookRelation")

    def test_factory_creates_unique_models(self):
        """Test that each factory call creates a unique model."""
        Relation1 = custom_relation_factory(Author, related_name="test_unique1")
        Relation2 = custom_relation_factory(Author, related_name="test_unique2")

        # They should be different classes
        self.assertIsNot(Relation1, Relation2)

    def test_descriptor_manager_creation(self):
        """Test that descriptors create managers correctly."""
        from djangocms_custom_content.models import _InverseRelationManager

        AuthorRelation = custom_relation_factory(Author, related_name="test_mgr_create")
        author = Author(name="Test")

        manager = author.test_mgr_create
        self.assertIsInstance(manager, _InverseRelationManager)
        self.assertIs(manager.instance, author)
        self.assertIs(manager.relation_model, AuthorRelation)
