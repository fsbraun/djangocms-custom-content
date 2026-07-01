from cms.cms_toolbars import (
    ADMIN_MENU_IDENTIFIER,
    ADMINISTRATION_BREAK,
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
        Return the position for a custom content shortcut in the admin (site)
        menu.

        Entries are grouped directly above the ``ADMINISTRATION_BREAK`` and
        ordered alphabetically among themselves, following the convention used
        by djangocms-stories and djangocms-alias. The first menu item (the
        current site entry) is always kept in place.

        Note that django CMS core adds the ``SHORTCUTS_BREAK`` *below* the
        ``ADMINISTRATION_BREAK`` (near the "Logout" entry), so it cannot be
        used as an upper anchor for the shortcut region -- the
        ``ADMINISTRATION_BREAK`` is the only reliable boundary.

        Args:
            ``admin_menu``: The CMS admin menu instance to inspect and modify.
            ``item_name``: The menu item name used for alphabetical ordering.

        Returns:
            The integer position where the item should be inserted.
        """
        end = admin_menu.find_first(Break, identifier=ADMINISTRATION_BREAK)
        if not end:
            # If the administration break doesn't exist yet, add it so the
            # shortcut has a stable boundary to sort against.
            admin_menu.add_break(ADMINISTRATION_BREAK)
            end = admin_menu.find_first(Break, identifier=ADMINISTRATION_BREAK)

        # Keep the first item (the current site / "Users" entry) in place and
        # sort alphabetically within the region up to the administration break.
        items = admin_menu.get_items()[1 : end.index]
        for idx, item in enumerate(items):
            try:
                if force_str(item_name.lower()) < force_str(item.name.lower()):  # noqa: E501
                    return idx + 1
            except AttributeError:
                # Breaks and some item types do not have a 'name' attribute.
                pass
        return end.index

    def add_shortcut_links(self):
        """Add admin-menu shortcut links for content that opted in.

        A model is included when its content sets ``admin_menu = True`` on its
        ``CMSConfig``. The linked changelist is the grouper's for grouper-backed
        content, or the content model's own for plain (grouper-less) content
        such as ``FlatCategory`` (see ``admin_menu_models`` in the app config).
        """
        admin_menu = self.toolbar.get_or_create_menu(ADMIN_MENU_IDENTIFIER)

        for model in self.config.admin_menu_models:
            if self.request.user.has_perm(f"{model._meta.app_label}.view_{model._meta.model_name}"):
                name = force_str(model._meta.verbose_name_plural.title())
                url = admin_reverse(f"{model._meta.app_label}_{model._meta.model_name}_changelist")
                admin_menu.add_sideframe_item(
                    name,
                    url=url,
                    position=self.get_insert_position(admin_menu, name),
                )

    def add_content_object_menu(self):
        """Add menu entries for the current grouper instance."""
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
        """Populate the toolbar with custom content entries."""

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


toolbar_pool.register(CustomContentToolbar)
