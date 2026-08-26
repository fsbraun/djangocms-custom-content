"""Two app hook instances of the same app, as two CMS pages would produce.

django CMS registers one resolver per app hook page: same application namespace,
different instance namespace. Reversing without ``current_app`` therefore always
lands on the first one.
"""

from django.urls import include, path

from tests.urls_apphooks import _get_person_apphook

apphook = _get_person_apphook()
if apphook is None:  # pragma: no cover - the app hook is registered at startup
    urlpatterns = []
else:
    urls = apphook.get_urls() if hasattr(apphook, "get_urls") else apphook().get_urls()
    urlpatterns = [
        path("team/", include((urls, "person"), namespace="team")),
        path("board/", include((urls, "person"), namespace="board")),
    ]
