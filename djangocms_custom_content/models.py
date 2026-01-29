from cms.models import CMSPlugin
from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomContent(CMSPlugin):
    """
    Custom content plugin model for flexible template-based content blocks.
    """

    template = models.CharField(
        _("Template"),
        max_length=255,
        help_text=_("The template to use for rendering this content block."),
    )

    content = models.TextField(
        _("Content"),
        blank=True,
        help_text=_("Custom content for this block."),
    )

    class Meta:
        verbose_name = _("Custom Content")
        verbose_name_plural = _("Custom Contents")

    def __str__(self):
        return self.template or str(self.pk)
