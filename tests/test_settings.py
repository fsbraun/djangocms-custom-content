import os

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sites",
    "django.contrib.sessions",
    "django.contrib.admin",
    "django.contrib.messages",
    "easy_thumbnails",
    "filer",
    "cms",
    "menus",
    "treebeard",
    "sekizai",
    "djangocms_custom_content",
    "djangocms_custom_content.contrib.blog",
    "djangocms_custom_content.contrib.people",
    "tests.test_app",
]

try:  # V4 test?
    import djangocms_versioning  # noqa

    INSTALLED_APPS += [
        "djangocms_versioning",
    ]
except ImportError:  # Nope
    pass

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "cms.middleware.user.CurrentUserMiddleware",
    "cms.middleware.page.CurrentPageMiddleware",
    "cms.middleware.toolbar.ToolbarMiddleware",
    "cms.middleware.language.LanguageCookieMiddleware",
]

CMS_LANGUAGES = {
    1: [
        {
            "code": "en",
            "name": "English",
        }
    ]
}

LANGUAGE_CODE = "en"
ALLOWED_HOSTS = ["localhost"]

SECRET_KEY = "fake-key"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(os.path.dirname(__file__), "templates"),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "sekizai.context_processors.sekizai",
                "cms.context_processors.cms_settings",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "mydatabase",
    }
}

CMS_TEMPLATES = (("page.html", "Page"),)

SITE_ID = 1

STATIC_URL = "/static/"

ROOT_URLCONF = "tests.urls"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CMS_CONFIRM_VERSION4 = True  # Needed for v4, neglected in v3
