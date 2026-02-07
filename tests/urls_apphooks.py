from cms.apphook_pool import apphook_pool
from django.urls import include, path


def _get_person_apphook():
    if hasattr(apphook_pool, "get_apphook"):
        apphook = apphook_pool.get_apphook("PersonApp")
        if apphook is not None:
            return apphook
        apphook = apphook_pool.get_apphook("person")
        if apphook is not None:
            return apphook

    if hasattr(apphook_pool, "get_apphooks"):
        for apphook in apphook_pool.get_apphooks():
            if getattr(apphook, "__name__", None) == "PersonApp" or getattr(apphook, "app_name", None) == "person":
                return apphook

    apps = getattr(apphook_pool, "apps", None)
    if isinstance(apps, dict):
        for apphook in apps.values():
            if getattr(apphook, "__name__", None) == "PersonApp" or getattr(apphook, "app_name", None) == "person":
                return apphook

    return None


apphook = _get_person_apphook()
if apphook is None:
    urlpatterns = []
else:
    urls = apphook.get_urls() if hasattr(apphook, "get_urls") else apphook().get_urls()
    app_name = getattr(apphook, "app_name", "person")
    urlpatterns = [path("", include((urls, app_name), namespace=app_name))]
