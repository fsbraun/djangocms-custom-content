"""Coverage for :func:`djangocms_custom_content.helpers.get_custom_config`.

The registry lookup is exercised throughout the suite by the contrib apps. These
tests cover the structural fallback, which only runs for a model django CMS has
not registered -- because its app ships no ``cms_config``, because the extension
has not run yet, or because django CMS is not installed at all.
"""

from unittest import mock

from django.apps import apps
from django.db import models
from django.test import SimpleTestCase
from django.test.utils import isolate_apps

from djangocms_custom_content.helpers import get_custom_config
from djangocms_custom_content.models import CustomContentMixin, CustomGrouperMixin


@isolate_apps("tests.test_app")
class GetCustomConfigRegistryTests(SimpleTestCase):
    def test_registered_entry_wins_over_derivation(self):
        """The registry is authoritative, so its entry is returned even when
        inspecting the model would produce something else."""

        class Topic(CustomGrouperMixin, models.Model):
            class Meta:
                app_label = "test_app"

        class TopicContent(CustomContentMixin, models.Model):
            topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
            language = models.CharField(max_length=8)

            class Meta:
                app_label = "test_app"

        # Deliberately disagrees with what the fallback would derive below.
        registered = (Topic, "grouper_named_by_cms_config", False)
        cms_config = apps.get_app_config("djangocms_custom_content").cms_config

        with mock.patch.dict(cms_config.custom_content_groupers, {TopicContent: registered}):
            self.assertEqual(get_custom_config(TopicContent), registered)

        self.assertEqual(get_custom_config(TopicContent), (Topic, "topic", True))


@isolate_apps("tests.test_app")
class GetCustomConfigFallbackTests(SimpleTestCase):
    """The fallback derives the same tuple by inspecting the model itself."""

    def test_derives_grouper_and_language_from_an_unregistered_model(self):
        class Topic(CustomGrouperMixin, models.Model):
            class Meta:
                app_label = "test_app"

        class TopicContent(CustomContentMixin, models.Model):
            topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
            language = models.CharField(max_length=8)

            class Meta:
                app_label = "test_app"

        self.assertEqual(get_custom_config(TopicContent), (Topic, "topic", True))

    def test_language_flag_is_false_without_a_language_field(self):
        class Topic(CustomGrouperMixin, models.Model):
            class Meta:
                app_label = "test_app"

        class TopicContent(CustomContentMixin, models.Model):
            topic = models.ForeignKey(Topic, on_delete=models.CASCADE)

            class Meta:
                app_label = "test_app"

        self.assertEqual(get_custom_config(TopicContent), (Topic, "topic", False))

    def test_foreign_keys_to_non_grouper_models_are_ignored(self):
        class Author(models.Model):
            class Meta:
                app_label = "test_app"

        class Standalone(CustomContentMixin, models.Model):
            author = models.ForeignKey(Author, on_delete=models.CASCADE)
            language = models.CharField(max_length=8)

            class Meta:
                app_label = "test_app"

        self.assertEqual(get_custom_config(Standalone), (None, None, False))

    def test_falls_back_when_the_cms_registry_is_unavailable(self):
        """No ``cms_config`` yet: the extension has not run, or there is no django CMS."""

        class Topic(CustomGrouperMixin, models.Model):
            class Meta:
                app_label = "test_app"

        class TopicContent(CustomContentMixin, models.Model):
            topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
            language = models.CharField(max_length=8)

            class Meta:
                app_label = "test_app"

        app_config = apps.get_app_config("djangocms_custom_content")
        with mock.patch.object(app_config, "cms_config", None):
            self.assertEqual(get_custom_config(TopicContent), (Topic, "topic", True))
