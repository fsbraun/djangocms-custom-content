import pytest
from cms.apphook_pool import apphook_pool
from django.test import TestCase, override_settings

from djangocms_custom_content.contrib.blog.models import BlogPostContent
from djangocms_custom_content.contrib.people.models import Person, PersonContent

pytestmark = pytest.mark.django_db


def _get_apphook_from_pool(name: str, app_name: str):
    if hasattr(apphook_pool, "get_apphook"):
        apphook = apphook_pool.get_apphook(name)
        if apphook is not None:
            return apphook
        apphook = apphook_pool.get_apphook(app_name)
        if apphook is not None:
            return apphook

    if hasattr(apphook_pool, "get_apphooks"):
        for apphook in apphook_pool.get_apphooks():
            if getattr(apphook, "__name__", None) == name or getattr(apphook, "app_name", None) == app_name:
                return apphook

    apps = getattr(apphook_pool, "apps", None)
    if isinstance(apps, dict):
        for apphook in apps.values():
            if getattr(apphook, "__name__", None) == name or getattr(apphook, "app_name", None) == app_name:
                return apphook

    return None


class ApphookGenerationTests(TestCase):
    def test_person_apphook_registered(self):
        apphook = _get_apphook_from_pool("PersonApp", "person")
        self.assertIsNotNone(apphook)
        self.assertEqual(getattr(apphook, "app_name", None), "person")

    def test_person_apphook_urls(self):
        apphook = _get_apphook_from_pool("PersonApp", "person")
        self.assertIsNotNone(apphook)

        urls = apphook.get_urls() if hasattr(apphook, "get_urls") else apphook().get_urls()
        self.assertEqual(len(urls), 1)
        self.assertEqual(urls[0].pattern._route, "<slug:slug>/")

    def test_person_content_has_absolute_url(self):
        self.assertTrue(callable(getattr(PersonContent, "get_absolute_url", None)))

    @override_settings(ROOT_URLCONF="tests.urls_apphooks")
    def test_person_content_get_absolute_url(self):
        person = Person.objects.create()
        content = PersonContent.objects.create(
            person=person,
            name="Jane Doe",
            role="Developer",
            description="Test",
            slug="jane-doe",
        )

        self.assertEqual(content.get_absolute_url(), "/jane-doe/")

    def test_no_blog_apphook_registered(self):
        apphook = _get_apphook_from_pool("BlogPostApp", "blogpost")
        self.assertIsNone(apphook)
        self.assertFalse(callable(getattr(BlogPostContent, "get_absolute_url", None)))
