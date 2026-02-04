from cms.toolbar_base import CMSToolbar
from cms.toolbar_pool import toolbar_pool
from cms.utils.urlutils import admin_reverse

from django.apps import apps
from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe


@toolbar_pool.register
class CustomContentToolbar(CMSToolbar):
    """
    Toolbar for djangocms-custom-content.
    
    Adds a settings icon button to the right toolbar.
    """

    class Media:
        css = {
            "all": ("djangocms_custom_content/icon.css",)
        }

    def add_menu(self):
        """Add menu for the grouper model."""
        # Get verbose name from the grouper model
        menu_name = self.grouper._meta.verbose_name_plural.title()
        
        # Create the menu
        menu = self.toolbar.get_or_create_menu(
            f"custom-content-{self.grouper._meta.model_name}",
            menu_name,
        )
        
        # Check permissions
        user = self.request.user
        model = self.grouper.__class__
        can_change = user.has_perm(f"{model._meta.app_label}.change_{model._meta.model_name}")
        can_add = user.has_perm(f"{model._meta.app_label}.add_{model._meta.model_name}")
        can_view = user.has_perm(f"{model._meta.app_label}.view_{model._meta.model_name}")
        
        # Add Settings item (change view in modal)
        change_url = admin_reverse(
            f"{self.grouper._meta.app_label}_{self.grouper._meta.model_name}_change",
            args=(self.grouper.pk,)
        )
        menu.add_modal_item(_("Settings"), url=change_url, disabled=not can_change)
        
        # Add Add item (add view in modal)
        add_url = admin_reverse(
            f"{self.grouper._meta.app_label}_{self.grouper._meta.model_name}_add"
        )
        menu.add_modal_item(_("Add"), url=add_url, disabled=not can_add)
        
        # Add Show all items (changelist view in sidebar)
        changelist_url = admin_reverse(
            f"{self.grouper._meta.app_label}_{self.grouper._meta.model_name}_changelist"
        )
        menu.add_sideframe_item(_("Show all items"), url=changelist_url, disabled=not (can_view or can_change))


    def populate(self):
        """Add custom content settings button to toolbar."""

        content = self.toolbar.get_object()
        config = apps.get_app_config("djangocms_custom_content").cms_config
        if content.__class__ not in config.custom_content_groupers:
            return

        self.grouper = getattr(content, config.custom_content_groupers[content.__class__][1], None)

        if not self.grouper:
            return

        self.add_menu()

        # Add a settings icon button to the right toolbar if enabled
        if getattr(settings, 'CMS_SETTINGS_SHORTCUT', True):
            url = admin_reverse(f"{self.grouper._meta.app_label}_{self.grouper._meta.model_name}_change", args=(self.grouper.pk,))
            self.toolbar.add_modal_button(
                mark_safe("<span class='cms-icon cms-icon-settings'></span>"),
                url=url,
                side=self.toolbar.RIGHT,
            )
