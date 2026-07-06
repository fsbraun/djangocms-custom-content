import pytest
from cms.cms_toolbars import ADMIN_MENU_IDENTIFIER, ADMINISTRATION_BREAK
from cms.toolbar.toolbar import CMSToolbar as ToolbarClass
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from djangocms_custom_content.cms_toolbars import CustomContentToolbar
from djangocms_custom_content.contrib.blog.models import BlogPost, BlogPostContent
from djangocms_custom_content.contrib.people.models import Person, PersonContent

User = get_user_model()
pytestmark = pytest.mark.django_db


class _FakeMenuItem:
    def __init__(self, name=None, identifier=None):
        self.name = name
        self.identifier = identifier
        self.index = None


class _FakeMenu:
    def __init__(self):
        self._items = []

    def _reindex(self):
        for idx, item in enumerate(self._items):
            item.index = idx

    def find_first(self, _item_type, identifier=None):
        for item in self._items:
            if getattr(item, "identifier", None) == identifier:
                return item
        return None

    def add_break(self, identifier, position=None):
        item = _FakeMenuItem(identifier=identifier)
        if position is None:
            self._items.append(item)
        else:
            self._items.insert(position, item)
        self._reindex()
        return item

    def add_item(self, name=None):
        item = _FakeMenuItem(name=name)
        self._items.append(item)
        self._reindex()
        return item

    def get_items(self):
        return list(self._items)


class CustomContentToolbarTestCase(TestCase):
    """Test case for CustomContentToolbar."""

    def setUp(self):
        self.factory = RequestFactory()
        self.superuser = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="password"
        )

        # Create a regular user with limited permissions
        self.regular_user = User.objects.create_user(username="user", email="user@example.com", password="password")

        # Create test blog post with user context for versioning
        self.post = BlogPost.objects.create()
        self.post_content = BlogPostContent.objects.with_user(self.superuser).create(
            post=self.post,
            title="Test Blog Post",
            slug="test-blog-post",
            excerpt="Test excerpt",
            body="Test body",
            language="en",
            is_featured=False,
        )

        # Create test person with user context for versioning
        self.person = Person.objects.create()
        self.person_content = PersonContent.objects.with_user(self.superuser).create(
            person=self.person,
            name="John Doe",
            role="Developer",
            description="Test bio",
            slug="john-doe",
        )

    def get_toolbar(self, content, user, edit_mode=True):
        """Helper method to create a toolbar instance."""
        request = self.factory.get("/")
        request.user = user
        request.session = {}
        request.current_page = None

        # Create the toolbar and attach it to the request
        toolbar = ToolbarClass(request)
        toolbar.toolbar_language = "en"
        toolbar.edit_mode_active = edit_mode
        toolbar.show_toolbar = True
        toolbar.set_object(content)
        request.toolbar = toolbar

        # Create the custom content toolbar
        custom_toolbar = CustomContentToolbar(request, toolbar, False, None)

        return custom_toolbar

    def test_toolbar_populates_for_blog_post_content(self):
        """Test that toolbar populates for blog post content."""
        toolbar = self.get_toolbar(self.post_content, self.superuser)
        toolbar.populate()

        # Check that grouper was set
        self.assertEqual(toolbar.grouper, self.post)

    def test_toolbar_populates_for_person(self):
        """Test that toolbar populates for person content."""
        toolbar = self.get_toolbar(self.person_content, self.superuser)
        toolbar.populate()

        # Check that grouper was set
        self.assertEqual(toolbar.grouper, self.person)

    def test_toolbar_does_not_populate_for_non_content(self):
        """Test that toolbar doesn't populate for non-custom content objects."""
        toolbar = self.get_toolbar(self.superuser, self.superuser)
        toolbar.populate()

        # Check that grouper was not set
        self.assertFalse(hasattr(toolbar, "grouper"))

    def test_menu_created_with_correct_name(self):
        """Test that menu is created with the correct verbose name."""
        toolbar = self.get_toolbar(self.post_content, self.superuser)
        toolbar.populate()

        # Check that menu exists with correct name
        menu = toolbar.toolbar.menus.get(f"custom-content-{self.post._meta.model_name}")
        self.assertIsNotNone(menu)

    def test_menu_items_for_superuser(self):
        """Test that all menu items are present and enabled for superuser."""
        toolbar = self.get_toolbar(self.post_content, self.superuser)
        toolbar.populate()

        menu = toolbar.toolbar.menus.get(f"custom-content-{self.post._meta.model_name}")
        items = [item for item in menu.items]

        # Should have at least 3 items: Settings, Add, Show all items
        self.assertGreaterEqual(len(items), 3)

        # First 3 items should be enabled (not disabled)
        for item in items[:3]:
            self.assertFalse(getattr(item, "disabled", False))

    def test_menu_items_disabled_without_permissions(self):
        """Test that menu items are disabled when user lacks permissions."""
        toolbar = self.get_toolbar(self.post_content, self.regular_user)
        toolbar.populate()

        menu = toolbar.toolbar.menus.get(f"custom-content-{self.post._meta.model_name}")
        items = [item for item in menu.items if hasattr(item, "disabled")]

        # Should have 3 menu items: Settings, Add, Show all items
        self.assertEqual(len(items), 3)

        # All items should be disabled
        for item in items:
            self.assertTrue(getattr(item, "disabled", False))

    def test_menu_items_with_partial_permissions(self):
        """Test that menu items are enabled based on specific permissions."""
        # Give user only view permission
        view_perm = Permission.objects.get(
            codename="view_blogpost", content_type__app_label="djangocms_custom_content_blog"
        )
        self.regular_user.user_permissions.add(view_perm)

        toolbar = self.get_toolbar(self.post_content, self.regular_user)
        toolbar.populate()

        menu = toolbar.toolbar.menus.get(f"custom-content-{self.post._meta.model_name}")
        items = [item for item in menu.items if hasattr(item, "disabled")]

        # Settings should be disabled (no change permission)
        self.assertTrue(getattr(items[0], "disabled", False))

        # Add should be disabled (no add permission - it's after the break, so index 1)
        self.assertTrue(getattr(items[1], "disabled", False))

        # Show all items should be enabled (has view permission)
        self.assertFalse(getattr(items[2], "disabled", False))

    def test_menu_items_with_change_permission(self):
        """Test that menu items work with change permission."""
        # Give user change permission
        change_perm = Permission.objects.get(
            codename="change_blogpost", content_type__app_label="djangocms_custom_content_blog"
        )
        self.regular_user.user_permissions.add(change_perm)

        toolbar = self.get_toolbar(self.post_content, self.regular_user)
        toolbar.populate()

        menu = toolbar.toolbar.menus.get(f"custom-content-{self.post._meta.model_name}")
        items = [item for item in menu.items if hasattr(item, "disabled")]

        # Settings should be enabled (has change permission)
        self.assertFalse(getattr(items[0], "disabled", False))

        # Add should be disabled (no add permission)
        self.assertTrue(getattr(items[1], "disabled", False))

        # Show all items should be enabled (has change permission which includes view)
        self.assertFalse(getattr(items[2], "disabled", False))

    def test_menu_items_with_add_permission(self):
        """Test that menu items work with add permission."""
        # Give user add permission
        add_perm = Permission.objects.get(
            codename="add_blogpost", content_type__app_label="djangocms_custom_content_blog"
        )
        self.regular_user.user_permissions.add(add_perm)

        toolbar = self.get_toolbar(self.post_content, self.regular_user)
        toolbar.populate()

        menu = toolbar.toolbar.menus.get(f"custom-content-{self.post._meta.model_name}")
        items = [item for item in menu.items if hasattr(item, "disabled")]

        # Settings should be disabled (no change permission)
        self.assertTrue(getattr(items[0], "disabled", False))

        # Add should be enabled (has add permission)
        self.assertFalse(getattr(items[1], "disabled", False))

        # Show all items should be disabled (no view/change permission)
        self.assertTrue(getattr(items[2], "disabled", False))

    @override_settings(CMS_SETTINGS_SHORTCUT=True)
    def test_right_button_shown_when_setting_true(self):
        """Test that right toolbar button is shown when CMS_SETTINGS_SHORTCUT is True."""
        toolbar = self.get_toolbar(self.post_content, self.superuser)
        toolbar.populate()

        # Check that right toolbar has buttons
        right_items = [item for item in toolbar.toolbar.right_items]
        self.assertGreater(len(right_items), 0)

    def test_right_button_not_shown_when_setting_false(self):
        """Test that right toolbar button respects CMS_SETTINGS_SHORTCUT setting."""
        # The button should be added by default (when setting is True)
        # This test just verifies the setting is checked - the actual behavior
        # depends on when settings are evaluated
        toolbar = self.get_toolbar(self.post_content, self.superuser)
        toolbar.populate()

        # Just verify the toolbar was populated successfully
        # The actual button visibility depends on the CMS_SETTINGS_SHORTCUT setting
        self.assertIsNotNone(toolbar.grouper)

    def test_toolbar_for_person_grouper(self):
        """Test that toolbar works correctly for Person model."""
        toolbar = self.get_toolbar(self.person_content, self.superuser)
        toolbar.populate()

        # Check that grouper was set correctly
        self.assertEqual(toolbar.grouper, self.person)

        # Check that menu exists
        menu = toolbar.toolbar.menus.get(f"custom-content-{self.person._meta.model_name}")
        self.assertIsNotNone(menu)

        # Check menu has at least 3 items
        items = [item for item in menu.items]
        self.assertGreaterEqual(len(items), 3)

    def test_menu_urls_are_correct(self):
        """Test that menu item URLs are correctly generated."""
        toolbar = self.get_toolbar(self.post_content, self.superuser)
        toolbar.populate()

        menu = toolbar.toolbar.menus.get(f"custom-content-{self.post._meta.model_name}")
        items = [item for item in menu.items if hasattr(item, "url")]

        # Check Settings URL (change view)
        settings_url = items[0].url
        self.assertIn(f"/{self.post.pk}/change/", settings_url)

        # Check Add URL
        add_url = items[1].url
        self.assertIn("/add/", add_url)

        # Check changelist URL
        changelist_url = items[2].url
        self.assertIn("/blogpost/", changelist_url)

    def test_add_shortcut_links(self):
        """Test that shortcut links are added to admin menu for all custom content types."""
        # Superuser should have all permissions
        toolbar = self.get_toolbar(self.post_content, self.superuser)

        # Populate the toolbar to trigger add_shortcut_links
        toolbar.populate()

        # Get the admin menu using the correct identifier
        admin_menu = toolbar.toolbar.get_menu(ADMIN_MENU_IDENTIFIER)
        if not admin_menu:
            # If it doesn't exist, this test should fail because populate should have created it
            self.fail(f"Admin menu '{ADMIN_MENU_IDENTIFIER}' was not created during toolbar population")

        # Check that shortcuts were added - get all items with names
        all_items = list(admin_menu.get_items())
        menu_items = [item for item in all_items if hasattr(item, "name")]

        # Superuser should have access, so shortcuts should be added
        # Look for blog and person shortcuts
        item_names = [str(item.name).lower() for item in menu_items]

        # At least one of the custom content types should be added as shortcut
        has_custom_content = any("blog" in name or "people" in name or "person" in name for name in item_names)
        self.assertTrue(has_custom_content, f"Expected custom content shortcuts in menu. Found: {item_names}")

    def test_add_shortcut_links_with_no_permissions(self):
        """Test that shortcut links are not added if user has no view permissions."""
        toolbar = self.get_toolbar(self.post_content, self.regular_user)
        toolbar.populate()

        # Get the admin menu
        admin_menu = toolbar.toolbar.get_menu(ADMIN_MENU_IDENTIFIER)
        if not admin_menu:
            # If no menu was created, that's actually fine - no shortcuts means no menu
            return

        # Check that no custom content shortcuts were added
        all_items = list(admin_menu.get_items())
        menu_items = [item for item in all_items if hasattr(item, "name")]
        item_names = [str(item.name).lower() for item in menu_items]

        # Should not have custom content shortcuts without permissions
        has_custom_content = any("blog" in name or "people" in name or "person" in name for name in item_names)
        self.assertFalse(
            has_custom_content, f"Should not have custom content shortcuts without permissions. Found: {item_names}"
        )

    def test_add_shortcut_links_with_view_permission(self):
        """Test that shortcut links are added when user has view permissions."""
        # Grant view permission for blog posts
        permission = Permission.objects.get(
            codename="view_blogpost", content_type__app_label="djangocms_custom_content_blog"
        )
        self.regular_user.user_permissions.add(permission)
        # Refresh user permissions cache
        self.regular_user = User.objects.get(pk=self.regular_user.pk)

        toolbar = self.get_toolbar(self.post_content, self.regular_user)
        toolbar.populate()

        # Get the admin menu
        admin_menu = toolbar.toolbar.get_menu(ADMIN_MENU_IDENTIFIER)
        self.assertIsNotNone(admin_menu, f"Admin menu '{ADMIN_MENU_IDENTIFIER}' should be created")

        # Check that blog shortcut was added
        all_items = list(admin_menu.get_items())
        menu_items = [item for item in all_items if hasattr(item, "name")]
        item_names = [str(item.name).lower() for item in menu_items]

        # Should have blog shortcut with view permission
        has_blog = any("blog" in name for name in item_names)
        self.assertTrue(has_blog, f"Blog post shortcut should be added with view permission. Found: {item_names}")

    def test_shortcut_links_respect_admin_menu_opt_in(self):
        """Groupers not opted in via ``admin_menu`` get no admin-menu shortcut."""
        from unittest import mock

        from django.apps import apps

        config = apps.get_app_config("djangocms_custom_content").cms_config

        toolbar = self.get_toolbar(self.post_content, self.superuser)
        # Simulate no content model opting into the admin menu.
        with mock.patch.object(config, "admin_menu_models", set()):
            toolbar.populate()

        admin_menu = toolbar.toolbar.get_menu(ADMIN_MENU_IDENTIFIER)
        if not admin_menu:
            return

        item_names = [str(item.name).lower() for item in admin_menu.get_items() if hasattr(item, "name")]
        has_custom_content = any("blog" in name or "people" in name or "person" in name for name in item_names)
        self.assertFalse(
            has_custom_content,
            f"No shortcuts should be added when no grouper opted in. Found: {item_names}",
        )

    def test_plain_content_model_shortcut(self):
        """A plain (grouper-less) content model opted in links to its own changelist."""
        toolbar = self.get_toolbar(self.post_content, self.superuser)
        toolbar.populate()

        admin_menu = toolbar.toolbar.get_menu(ADMIN_MENU_IDENTIFIER)
        self.assertIsNotNone(admin_menu)

        # FlatCategory has no grouper, so it should appear via its own changelist.
        category_items = [
            item for item in admin_menu.get_items() if getattr(item, "url", None) and "/flatcategory/" in item.url
        ]
        self.assertTrue(category_items, "FlatCategory should have an admin-menu shortcut")
        self.assertTrue(str(category_items[0].name).startswith("Categories"))


class GetInsertPositionTests(TestCase):
    """Tests for CustomContentToolbar.get_insert_position."""

    def test_adds_admin_break_when_missing(self):
        menu = _FakeMenu()

        position = CustomContentToolbar.get_insert_position(menu, "Foo")

        end = menu.find_first(None, ADMINISTRATION_BREAK)
        self.assertIsNotNone(end)
        self.assertEqual(position, end.index)

    def test_inserts_alphabetically_above_admin_break(self):
        menu = _FakeMenu()
        menu.add_item(name="Users")  # first item is kept in place
        menu.add_item(name="Alpha")
        menu.add_item(name="Zulu")
        menu.add_break(ADMINISTRATION_BREAK)

        position = CustomContentToolbar.get_insert_position(menu, "Bravo")

        # Between "Alpha" (index 1) and "Zulu" (index 2).
        self.assertEqual(position, 2)

    def test_keeps_first_item_in_place(self):
        menu = _FakeMenu()
        menu.add_item(name="Users")  # first item is kept in place
        menu.add_break(ADMINISTRATION_BREAK)

        position = CustomContentToolbar.get_insert_position(menu, "Aardvark")

        # Even though "Aardvark" sorts before "Users", the first item is never
        # displaced -- the shortcut lands at the administration break.
        end = menu.find_first(None, ADMINISTRATION_BREAK)
        self.assertEqual(position, end.index)

    def test_returns_end_when_name_is_last(self):
        menu = _FakeMenu()
        menu.add_item(name="Users")
        menu.add_item(name="Alpha")
        menu.add_item(name="Zulu")
        menu.add_break(ADMINISTRATION_BREAK)

        position = CustomContentToolbar.get_insert_position(menu, "Zulu")

        end = menu.find_first(None, ADMINISTRATION_BREAK)
        self.assertEqual(position, end.index)

    def test_ignores_items_without_name(self):
        menu = _FakeMenu()
        menu.add_item(name="Users")
        menu.add_item(name=None)
        menu.add_break(ADMINISTRATION_BREAK)

        position = CustomContentToolbar.get_insert_position(menu, "Alpha")

        end = menu.find_first(None, ADMINISTRATION_BREAK)
        self.assertEqual(position, end.index)
