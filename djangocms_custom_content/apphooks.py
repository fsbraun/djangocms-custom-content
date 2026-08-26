"""Declarative configuration for the generated app hook.

``CMSConfig.apphook`` accepts either ``True`` -- the conventional app hook, one
detail URL and nothing else -- or an :class:`AppHookConfig` describing what to
generate::

    class CMSConfig:
        apphook = AppHookConfig(
            detail_view=PersonDetailView,
            extra_urls=[path("<slug:slug>/vcard/", VCardView.as_view(), name="vcard")],
        )

``True`` is shorthand for ``AppHookConfig()``, so nothing changes for the common
case.

There is deliberately **no list view by default**. The page an app hook is
attached to is an ordinary CMS page, and listing content there is the job of the
"Custom content list" plugin -- which lets an editor put an introduction, an
image and the list on one page instead of inheriting a template nobody can edit.
See :doc:`../how-to/apphooks`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from django.urls import URLPattern


class AppHookConfig:
    """What to generate for a content model's app hook.

    Args:
        ``detail_view``: View class for a single object. Defaults to the generated
            ``DetailView``. A class is expected, not the result of ``as_view()``.
        ``list_view``: View class for the app hook root. Defaults to ``None`` --
            see the module docstring for why.
        ``extra_urls``: Extra URL patterns, registered *before* the detail route so
            a literal path can win over the slug pattern.
        ``slug_field``: Field the detail URL routes on. Defaults to ``"slug"`` when
            the content model has one, otherwise the primary key.
        ``namespace_field``: Field on the **grouper** naming the app hook instance
            this object belongs to. Set it to support more than one app hook page;
            leaving it unset keeps the current single-instance behaviour.
        ``app_name``: Application namespace. Defaults to the grouper model name,
            lowercased.
        ``name``: Human-readable name shown in the page's *Application* dropdown.
            Defaults to the grouper model name.
    """

    def __init__(
        self,
        detail_view: type | None = None,
        list_view: type | None = None,
        extra_urls: Sequence[URLPattern] = (),
        slug_field: str | None = None,
        namespace_field: str | None = None,
        app_name: str | None = None,
        name: str | None = None,
    ) -> None:
        self.detail_view = detail_view
        self.list_view = list_view
        self.extra_urls = list(extra_urls)
        self.slug_field = slug_field
        self.namespace_field = namespace_field
        self.app_name = app_name
        self.name = name

    @classmethod
    def coerce(cls, value: Any) -> AppHookConfig | None:
        """Normalise a ``CMSConfig.apphook`` declaration.

        ``True`` becomes a default config, ``False``/``None`` means no app hook,
        and a config is returned unchanged.
        """
        if isinstance(value, cls):
            return value
        if value:
            return cls()
        return None

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"{type(self).__name__}(detail_view={self.detail_view!r}, list_view={self.list_view!r}, "
            f"extra_urls={len(self.extra_urls)}, slug_field={self.slug_field!r}, "
            f"namespace_field={self.namespace_field!r}, app_name={self.app_name!r})"
        )
