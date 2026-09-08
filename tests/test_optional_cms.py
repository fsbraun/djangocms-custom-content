import subprocess
import sys

from cms.models.fields import PlaceholderRelationField
from cms.models.managers import ContentAdminManager
from django.db import models
from django.db.migrations.state import ModelState
from django.test import SimpleTestCase
from django.test.utils import isolate_apps

from djangocms_custom_content.cms_config import _configure_cms_model
from djangocms_custom_content.models import AbstractCustomContent


class CMSModelConfigurationTests(SimpleTestCase):
    @isolate_apps("tests.test_app")
    def test_cms_configuration_does_not_change_migration_state(self):
        class ExampleContent(AbstractCustomContent):
            title = models.CharField(max_length=100)

            class Meta:
                app_label = "test_app"

        state_without_cms_config = ModelState.from_model(ExampleContent)

        _configure_cms_model(ExampleContent)

        state_with_cms_config = ModelState.from_model(ExampleContent)
        self.assertEqual(state_with_cms_config, state_without_cms_config)
        self.assertIsInstance(
            next(field for field in ExampleContent._meta.private_fields if field.name == "placeholders"),
            PlaceholderRelationField,
        )
        self.assertIsInstance(ExampleContent.admin_manager, ContentAdminManager)
        self.assertEqual(ExampleContent._default_manager.name, "objects")


class WithoutDjangoCMSIntegrationTests(SimpleTestCase):
    def test_models_work_when_django_cms_is_unavailable(self):
        script = r"""
import sys
from importlib.abc import MetaPathFinder


class RejectCMSImports(MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "cms" or fullname.startswith("cms."):
            raise ImportError("django CMS is intentionally unavailable")
        return None


sys.meta_path.insert(0, RejectCMSImports())

from django.conf import settings

settings.configure(
    INSTALLED_APPS=["djangocms_custom_content"],
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
    SECRET_KEY="test",
    USE_I18N=True,
)

import django

django.setup()

from django.db import connection, models
from djangocms_custom_content.models import (
    ContentAdminManager,
    CustomContentManager,
    CustomContentMixin,
    CustomGrouperMixin,
)


class Article(CustomGrouperMixin, models.Model):
    class Meta:
        app_label = "djangocms_custom_content"


class ArticleContent(CustomContentMixin, models.Model):
    objects = CustomContentManager()
    admin_manager = ContentAdminManager()

    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    language = models.CharField(max_length=8)
    title = models.CharField(max_length=100)

    class Meta:
        app_label = "djangocms_custom_content"


assert not hasattr(ArticleContent, "placeholders")

with connection.schema_editor() as schema_editor:
    schema_editor.create_model(Article)
    schema_editor.create_model(ArticleContent)

article = Article.objects.create()
content = ArticleContent.objects.with_user(object()).create(
    article=article,
    language="en",
    title="No CMS required",
)

assert article.get_content("en") == content
assert article.get_admin_content("en") == content
assert ArticleContent.admin_manager.latest_content().get() == content
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
