from cms.cms_toolbars import (
    ADMIN_MENU_IDENTIFIER,
    ADMINISTRATION_BREAK,
    LANGUAGE_MENU_IDENTIFIER,
    SHORTCUTS_BREAK,
)
from cms.toolbar.items import Break
from cms.toolbar_base import CMSToolbar
from cms.toolbar_pool import toolbar_pool
from cms.utils.urlutils import admin_reverse
from django.apps import apps
from django.conf import settings
from django.utils.encoding import force_str
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _


@toolbar_pool.register
class CustomContentToolbar(CMSToolbar):
    """
    Toolbar for djangocms-custom-content.

    Adds a settings icon button to the right toolbar.
    """

    class Media:
        css = {"all": ("djangocms_custom_content/icon.css",)}

    @classmethod
    def get_insert_position(cls, admin_menu, item_name):
        """
        Ensures that there is a SHORTCUTS_BREAK and returns a position for an
        alphabetical position against all items between SHORTCUTS_BREAK, and
        the ADMINISTRATION_BREAK.
        """
        start = admin_menu.find_first(Break, identifier=SHORTCUTS_BREAK)

        if not start:
            end = admin_menu.find_first(Break, identifier=ADMINISTRATION_BREAK)
            if not end:
                # If neither break exists, add both breaks at the end
                admin_menu.add_break(SHORTCUTS_BREAK)
                admin_menu.add_break(ADMINISTRATION_BREAK)
                start = admin_menu.find_first(Break, identifier=SHORTCUTS_BREAK)
                end = admin_menu.find_first(Break, identifier=ADMINISTRATION_BREAK)
            else:
                admin_menu.add_break(SHORTCUTS_BREAK, position=end.index)
                start = admin_menu.find_first(Break, identifier=SHORTCUTS_BREAK)

        end = admin_menu.find_first(Break, identifier=ADMINISTRATION_BREAK)
        if not end:
            # If ADMINISTRATION_BREAK doesn't exist, add it after SHORTCUTS_BREAK
            admin_menu.add_break(ADMINISTRATION_BREAK)
            end = admin_menu.find_first(Break, identifier=ADMINISTRATION_BREAK)

        items = admin_menu.get_items()[start.index + 1 : end.index]
        for idx, item in enumerate(items):
            try:
                if force_str(item_name.lower()) < force_str(item.name.lower()):  # noqa: E501
                    return idx + start.index + 1
            except AttributeError:
                # Some item types do not have a 'name' attribute.
                pass
        return end.index

    def add_shortcut_links(self):
        admin_menu = self.toolbar.get_or_create_menu(ADMIN_MENU_IDENTIFIER)

        for grouper, _field_name, _has_lang in self.config.custom_content_groupers.values():
            if self.request.user.has_perm(f"{grouper._meta.app_label}.view_{grouper._meta.model_name}"):
                name = force_str(grouper._meta.verbose_name_plural.title())
                url = admin_reverse(f"{grouper._meta.app_label}_{grouper._meta.model_name}_changelist")
                admin_menu.add_sideframe_item(
                    name,
                    url=url,
                    position=self.get_insert_position(admin_menu, name),
                )

    def add_content_object_menu(self):
        """Add menu for the grouper model."""
        # Get verbose name from the grouper model
        menu_name = self.grouper._meta.verbose_name.title()
        plural = self.grouper._meta.verbose_name_plural.title()

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
            f"{self.grouper._meta.app_label}_{self.grouper._meta.model_name}_change", args=(self.grouper.pk,)
        )
        menu.add_modal_item(_("%s settings") % menu_name, url=change_url, disabled=not can_change)
        menu.add_break()

        # Add Add item (add view in modal)
        add_url = admin_reverse(f"{self.grouper._meta.app_label}_{self.grouper._meta.model_name}_add")
        menu.add_modal_item(_("Add %s") % menu_name, url=add_url, disabled=not can_add)

        # Add Show all items (changelist view in sidebar)
        changelist_url = admin_reverse(f"{self.grouper._meta.app_label}_{self.grouper._meta.model_name}_changelist")
        menu.add_sideframe_item(_("Show all %s") % plural, url=changelist_url, disabled=not (can_view or can_change))

    def populate(self):
        """Add custom content settings button to toolbar."""

        content = self.toolbar.get_object()
        self.config = apps.get_app_config("djangocms_custom_content").cms_config

        self.add_shortcut_links()

        if content.__class__ not in self.config.custom_content_groupers:
            return

        self.grouper = getattr(content, self.config.custom_content_groupers[content.__class__][1], None)
        if not self.grouper:
            return

        self.add_content_object_menu()

        # Add a settings icon button to the right toolbar if enabled
        if getattr(settings, "CMS_SETTINGS_SHORTCUT", True):
            url = admin_reverse(
                f"{self.grouper._meta.app_label}_{self.grouper._meta.model_name}_change", args=(self.grouper.pk,)
            )
            self.toolbar.add_modal_button(
                mark_safe("<span class='cms-icon cms-icon-settings'></span>"),
                url=url,
                side=self.toolbar.RIGHT,
            )
