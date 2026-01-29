from cms.api import add_plugin
from django.test import TestCase

from djangocms_custom_content.cms_plugins import CustomContentPlugin
from djangocms_custom_content.models import CustomContent


class CustomContentPluginTestCase(TestCase):
    """Test cases for CustomContent plugin."""

    def test_plugin_instance(self):
        """Test plugin can be instantiated."""
        plugin = CustomContentPlugin()
        assert plugin.model == CustomContent
        assert plugin.name == "Custom Content"

    def test_model_str(self):
        """Test model string representation."""
        instance = CustomContent(template="test_template.html")
        assert str(instance) == "test_template.html"
