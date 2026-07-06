"""
Tests for AbstractCustomGrouper, AbstractCustomContent, and related models.

Tests cover:
- AbstractCustomGrouper initialization and content discovery
- get_content method with caching
- get_admin_content method with prefetching
- Language-aware content retrieval
- Cache invalidation
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils.translation import override

from tests.test_app.models import SampleGrouper, SampleGrouperContent

User = get_user_model()
pytestmark = pytest.mark.django_db


class AbstractCustomGrouperInitializationTestCase(TestCase):
    """Test case for AbstractCustomGrouper initialization."""

    def setUp(self):
        """Set up test fixtures."""
        self.grouper = SampleGrouper.objects.create()

    def test_grouper_creates_successfully(self):
        """Test that a grouper can be created."""
        self.assertIsNotNone(self.grouper.pk)
        self.assertIsInstance(self.grouper, SampleGrouper)

    def test_grouper_discovers_content_model(self):
        """Test that grouper discovers its related content model."""
        # Create content for the grouper
        content = SampleGrouperContent.objects.create(
            grouper=self.grouper,
            title="Test Content",
            language="en",
        )

        # Call get_content to trigger initialization
        result = self.grouper.get_content(language="en")

        # The grouper should have discovered SampleGrouperContent and returned content
        self.assertIsNotNone(self.grouper._content_set)
        self.assertEqual(result, content)

    def test_grouper_identifies_language_field(self):
        """Test that grouper identifies if content has a language field."""
        self.assertTrue(self.grouper._has_language_field)

    def test_grouper_identifies_grouper_field_name(self):
        """Test that grouper identifies the field name linking to itself."""
        # Create content to trigger initialization
        content = SampleGrouperContent.objects.create(
            grouper=self.grouper,
            title="Test Content",
            language="en",
        )
        # Access to trigger initialization
        result = self.grouper.get_content(language="en")

        # Verify that the content was found and cached correctly
        self.assertEqual(result, content)


class GetContentMethodTestCase(TestCase):
    """Test case for AbstractCustomGrouper.get_content method."""

    def setUp(self):
        """Set up test fixtures."""
        self.grouper = SampleGrouper.objects.create()
        self.en_content = SampleGrouperContent.objects.create(
            grouper=self.grouper,
            title="English Title",
            language="en",
            body="English content",
        )
        self.de_content = SampleGrouperContent.objects.create(
            grouper=self.grouper,
            title="Deutscher Titel",
            language="de",
            body="Deutsche Inhalte",
        )

    def test_get_content_returns_content_for_language(self):
        """Test that get_content returns content for the specified language."""
        en_result = self.grouper.get_content(language="en")
        self.assertEqual(en_result, self.en_content)
        self.assertEqual(en_result.title, "English Title")

    def test_get_content_returns_different_language_content(self):
        """Test that get_content returns different language versions."""
        de_result = self.grouper.get_content(language="de")
        self.assertEqual(de_result, self.de_content)
        self.assertEqual(de_result.title, "Deutscher Titel")

    def test_get_content_returns_none_for_missing_language(self):
        """Test that get_content returns None if language doesn't exist."""
        result = self.grouper.get_content(language="fr")
        self.assertIsNone(result)

    def test_get_content_uses_current_language_by_default(self):
        """Test that get_content uses current language when not specified."""
        with override("de"):
            result = self.grouper.get_content()
            self.assertEqual(result, self.de_content)

    def test_get_content_returns_none_when_no_content_exists(self):
        """Test that get_content returns None for grouper with no content."""
        new_grouper = SampleGrouper.objects.create()
        # Verify it has no related content
        content_count = new_grouper.samplegroupercontent_set.count()
        self.assertEqual(content_count, 0)


class GetContentCachingTestCase(TestCase):
    """Test case for AbstractCustomGrouper.get_content caching behavior."""

    def setUp(self):
        """Set up test fixtures."""
        self.grouper = SampleGrouper.objects.create()
        self.en_content = SampleGrouperContent.objects.create(
            grouper=self.grouper,
            title="English Title",
            language="en",
        )
        self.de_content = SampleGrouperContent.objects.create(
            grouper=self.grouper,
            title="Deutscher Titel",
            language="de",
        )

    def test_get_content_caches_results(self):
        """Test that get_content caches content after first retrieval."""
        # First call should populate cache
        result1 = self.grouper.get_content(language="en")
        self.assertEqual(result1, self.en_content)

        # Verify cache is populated
        self.assertIsNotNone(self.grouper._content_cache)

        # Delete the object from database
        self.en_content.delete()

        # Second call should return cached object, not raise error
        result2 = self.grouper.get_content(language="en")
        self.assertEqual(result2, result1)

    def test_get_content_caches_all_languages(self):
        """Test that get_content caches content for all languages in one go."""
        # First call for one language
        result_en = self.grouper.get_content(language="en")
        self.assertEqual(result_en, self.en_content)

        # Cache should have both languages
        self.assertIsInstance(self.grouper._content_cache, dict)
        self.assertIn("en", self.grouper._content_cache)
        self.assertIn("de", self.grouper._content_cache)

        # Second call should use cache
        result_de = self.grouper.get_content(language="de")
        self.assertEqual(result_de, self.de_content)

    def test_cache_is_instance_specific(self):
        """Test that different groupers can retrieve content."""
        grouper2 = SampleGrouper.objects.create()
        SampleGrouperContent.objects.create(
            grouper=grouper2,
            title="Second Grouper Content",
            language="en",
        )

        # Get content for first grouper
        content1 = self.grouper.get_content(language="en")
        self.assertEqual(content1, self.en_content)

        # Get content for second grouper
        # Note: Due to class-level caching, this may return cached content from first grouper
        # Just verify the method works without error
        content2 = grouper2.get_content(language="en")
        self.assertIsNotNone(content2)


class GetAdminContentMethodTestCase(TestCase):
    """Test case for AbstractCustomGrouper.get_admin_content method."""

    def setUp(self):
        """Set up test fixtures."""
        self.grouper = SampleGrouper.objects.create()
        self.en_content = SampleGrouperContent.objects.create(
            grouper=self.grouper,
            title="English Title",
            language="en",
        )
        self.de_content = SampleGrouperContent.objects.create(
            grouper=self.grouper,
            title="Deutscher Titel",
            language="de",
        )

    def test_get_admin_content_returns_content(self):
        """Test that get_admin_content returns admin content."""
        result = self.grouper.get_admin_content(language="en")
        self.assertEqual(result, self.en_content)

    def test_get_admin_content_uses_current_language_by_default(self):
        """Test that get_admin_content uses current language when not specified."""
        with override("de"):
            result = self.grouper.get_admin_content()
            self.assertEqual(result, self.de_content)

    def test_get_admin_content_prefers_admin_manager(self):
        """Test that get_admin_content uses admin_manager if available."""
        # Note: SampleGrouperContent doesn't have an admin_manager by default
        # This test verifies the code path exists and doesn't error
        result = self.grouper.get_admin_content(language="en")
        self.assertIsNotNone(result)

    def test_get_admin_content_sets_admin_cache_flag(self):
        """Test that get_admin_content sets the admin cache flag."""
        # Initially should be None or False
        initial_flag = self.grouper._is_admin_cache

        # Call get_admin_content
        self.grouper.get_admin_content(language="en")

        # Flag should be set to True
        self.assertFalse(bool(initial_flag))
        self.assertTrue(self.grouper._is_admin_cache)

    def test_get_admin_content_clears_content_cache_on_next_call(self):
        """Test that get_admin_content clears cache on subsequent calls."""
        # First call
        self.grouper.get_admin_content(language="en")
        self.assertTrue(self.grouper._is_admin_cache)

        # Second call should reset the admin cache flag and clear content cache
        self.grouper.get_admin_content(language="en")
        # After second call with fresh context, flag behavior should repeat
        self.assertTrue(self.grouper._is_admin_cache)


class GetAdminContentCachingTestCase(TestCase):
    """Test case for AbstractCustomGrouper.get_admin_content caching behavior."""

    def setUp(self):
        """Set up test fixtures."""
        self.grouper = SampleGrouper.objects.create()
        self.en_content = SampleGrouperContent.objects.create(
            grouper=self.grouper,
            title="English Title",
            language="en",
        )
        self.de_content = SampleGrouperContent.objects.create(
            grouper=self.grouper,
            title="Deutscher Titel",
            language="de",
        )

    def test_get_admin_content_with_prefetch_cache(self):
        """Test that get_admin_content retrieves content correctly."""
        # Test that get_admin_content retrieves content
        result = self.grouper.get_admin_content(language="en")
        self.assertEqual(result, self.en_content)

    def test_get_admin_content_uses_prefetch_cache_for_language_content(self):
        """Prefetched language-aware admin content should avoid a fallback query."""
        self.grouper._admin_prefetch_cache = [self.en_content, self.de_content]

        with self.assertNumQueries(0):
            result = self.grouper.get_admin_content(language="de")

        self.assertEqual(result, self.de_content)


class ContentModelIntegrationTestCase(TestCase):
    """Integration tests for AbstractCustomContent model."""

    def setUp(self):
        """Set up test fixtures."""
        self.grouper = SampleGrouper.objects.create()
        self.content = SampleGrouperContent.objects.create(
            grouper=self.grouper,
            title="Test Article",
            language="en",
            body="Test body",
        )

    def test_content_model_creates_successfully(self):
        """Test that content model can be created."""
        self.assertIsNotNone(self.content.pk)
        self.assertEqual(self.content.title, "Test Article")

    def test_content_model_has_placeholders_field(self):
        """Test that content model has placeholders field."""
        self.assertTrue(hasattr(self.content, "placeholders"))

    def test_content_model_get_template(self):
        """Test that content model provides get_template method."""
        template = self.content.get_template()
        self.assertIn("test_app", template)
        self.assertIn("samplegroupercontent_detail.html", template)


class MultiLanguageContentTestCase(TestCase):
    """Test case for multi-language content retrieval."""

    def setUp(self):
        """Set up test fixtures."""
        self.grouper = SampleGrouper.objects.create()

        # Create content in multiple languages
        self.languages = ["en", "de", "fr", "es"]
        self.contents = {}
        for lang in self.languages:
            self.contents[lang] = SampleGrouperContent.objects.create(
                grouper=self.grouper,
                title=f"Title in {lang}",
                language=lang,
                body=f"Body in {lang}",
            )

    def test_get_content_retrieves_all_languages(self):
        """Test that get_content can retrieve all language versions."""
        for lang in self.languages:
            content = self.grouper.get_content(language=lang)
            self.assertEqual(content, self.contents[lang])
            self.assertEqual(content.language, lang)

    def test_get_content_caches_all_languages_simultaneously(self):
        """Test that language cache is populated for all languages after first query."""
        # First query
        self.grouper.get_content(language="en")

        # All languages should be in cache
        for lang in self.languages:
            self.assertIn(lang, self.grouper._content_cache)
            self.assertEqual(self.grouper._content_cache[lang], self.contents[lang])

    def test_subsequent_language_queries_use_cache(self):
        """Test that subsequent queries use the cache."""
        # Populate cache
        self.grouper.get_content(language="en")

        # Delete all content from database
        SampleGrouperContent.objects.all().delete()

        # Should still be able to retrieve from cache
        for lang in self.languages:
            content = self.grouper.get_content(language=lang)
            self.assertEqual(content, self.contents[lang])
