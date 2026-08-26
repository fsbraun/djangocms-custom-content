"""Tests for the blog's paginated list plugin.

The app hook generates no list view, so this plugin is what fills an app hook's
root page. Pagination is driven by a ``page-<pk>`` query parameter so that two
list plugins on one page do not fight over ``?page=``.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from djangocms_custom_content.contrib.blog.cms_plugins import BlogPostListPlugin
from djangocms_custom_content.contrib.blog.models import BlogPost, BlogPostContent, BlogPostList

User = get_user_model()
pytestmark = pytest.mark.django_db


class BlogListTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser("admin", "admin@example.com", "pw")

    def make_post(self, title, slug, is_featured=False):
        from djangocms_versioning.constants import DRAFT
        from djangocms_versioning.models import Version

        post = BlogPost.objects.create()
        BlogPostContent.objects.with_user(self.user).create(
            post=post, title=title, slug=slug, excerpt="", body="", language="en", is_featured=is_featured
        )
        for version in Version.objects.filter_by_grouper(post).filter(state=DRAFT):
            version.publish(self.user)
        return post

    def render(self, instance, query=""):
        request = RequestFactory().get(f"/blog/{query}")
        return BlogPostListPlugin().render({"request": request}, instance, "content")

    def plugin(self, page_size=10, only_featured=False, pk=1):
        instance = BlogPostList(page_size=page_size, only_featured=only_featured)
        instance.pk = pk
        return instance


class ModelTests(BlogListTestBase):
    def test_str_is_the_verbose_name(self):
        self.assertEqual(str(BlogPostList()), "Blog post list")


class QuerysetTests(BlogListTestBase):
    def test_lists_published_posts(self):
        self.make_post("First", "first")
        self.make_post("Second", "second")

        titles = {post.title for post in self.plugin().get_queryset()}

        self.assertEqual(titles, {"First", "Second"})

    def test_only_featured_filters(self):
        self.make_post("Featured", "featured", is_featured=True)
        self.make_post("Plain", "plain")

        titles = {post.title for post in self.plugin(only_featured=True).get_queryset()}

        self.assertEqual(titles, {"Featured"})

    def test_unpublished_posts_are_left_out(self):
        from djangocms_versioning.constants import PUBLISHED
        from djangocms_versioning.models import Version

        post = self.make_post("Gone", "gone")
        self.make_post("Kept", "kept")
        Version.objects.filter_by_grouper(post).filter(state=PUBLISHED).first().unpublish(self.user)

        titles = {content.title for content in self.plugin().get_queryset()}

        self.assertEqual(titles, {"Kept"})


class PaginationTests(BlogListTestBase):
    def setUp(self):
        for index in range(5):
            self.make_post(f"Post {index}", f"post-{index}")

    def test_first_page_by_default(self):
        context = self.render(self.plugin(page_size=2))

        self.assertEqual(len(context["posts"]), 2)
        self.assertEqual(context["page_obj"].number, 1)
        self.assertEqual(context["paginator"].num_pages, 3)

    def test_requested_page_is_served(self):
        context = self.render(self.plugin(page_size=2, pk=7), query="?page-7=2")

        self.assertEqual(context["page_obj"].number, 2)

    def test_page_kwarg_is_namespaced_per_plugin(self):
        """Two lists on one page must paginate independently."""
        first, second = self.plugin(page_size=2, pk=7), self.plugin(page_size=2, pk=9)

        self.assertEqual(first.page_kwarg, "page-7")
        self.assertNotEqual(first.page_kwarg, second.page_kwarg)

        context = self.render(second, query="?page-7=2")
        self.assertEqual(context["page_obj"].number, 1, "the other plugin's page number must be ignored")

    def test_junk_page_falls_back_to_the_first(self):
        context = self.render(self.plugin(page_size=2, pk=7), query="?page-7=banana")

        self.assertEqual(context["page_obj"].number, 1)

    def test_out_of_range_shows_the_last_page(self):
        """A plugin must not 404 the whole page it sits on."""
        context = self.render(self.plugin(page_size=2, pk=7), query="?page-7=99")

        self.assertEqual(context["page_obj"].number, 3)

    def test_zero_page_size_disables_pagination(self):
        context = self.render(self.plugin(page_size=0))

        self.assertEqual(len(context["posts"]), 5)
        self.assertIsNone(context["page_obj"])

    def test_other_query_parameters_survive_page_links(self):
        context = self.render(self.plugin(page_size=2, pk=7), query="?page-7=2&tag=django")

        self.assertEqual(context["querystring"], "tag=django&")

    def test_querystring_is_empty_without_other_parameters(self):
        context = self.render(self.plugin(page_size=2, pk=7), query="?page-7=2")

        self.assertEqual(context["querystring"], "")

    def test_without_a_request_there_is_no_querystring(self):
        """The plugin can be rendered outside a request cycle (a preview, a test)."""
        from djangocms_custom_content.contrib.blog.cms_plugins import _querystring_without

        self.assertEqual(_querystring_without(None, "page-1"), "")

    def test_plugin_is_not_cached(self):
        """Output depends on the query string, so caching would pin page one."""
        self.assertFalse(BlogPostListPlugin.cache)


class RenderedMarkupTests(BlogListTestBase):
    def test_pagination_nav_links_carry_the_namespaced_parameter(self):
        from django.template.loader import render_to_string

        for index in range(3):
            self.make_post(f"Post {index}", f"post-{index}")
        context = self.render(self.plugin(page_size=2, pk=7))

        html = render_to_string("djangocms_custom_content_blog/blog_post_list.html", context)

        self.assertIn("page-7=2", html)
        self.assertIn("Page 1 of 2", html)

    def test_no_nav_when_everything_fits_on_one_page(self):
        from django.template.loader import render_to_string

        self.make_post("Only", "only")
        context = self.render(self.plugin(page_size=10))

        html = render_to_string("djangocms_custom_content_blog/blog_post_list.html", context)

        self.assertNotIn("dcc-pagination", html)
