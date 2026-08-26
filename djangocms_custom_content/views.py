import logging

from django.db import models
from django.http import Http404, HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from django.utils.translation import get_language
from django.views.generic import DetailView

from djangocms_custom_content.helpers import get_custom_config

logger = logging.getLogger(__name__)


class CustomDetailViewMixin:
    """Resolve the content object a detail URL points at.

    Two things the plain :class:`~django.views.generic.DetailView` does not do:

    * **Narrow to the active language.** A slug identifies content, and content of
      the same object exists once per language -- so without this filter a
      translated object matches its own slug more than once.
    * **Survive a slug that matches more than one object.** Uniqueness across
      objects is enforced by the versioning package, not here. If a duplicate
      slips through anyway, serving the first match is better than a 500; the
      duplicate is reported to the log so it can be cleaned up.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _, self.grouper_field_name, self.has_language_field = get_custom_config(self.model)

    def get_queryset(self):
        """Prefetch the grouper, and restrict to the active language."""
        queryset = super().get_queryset().select_related(self.grouper_field_name)
        language = get_language()
        if self.has_language_field and language:
            queryset = queryset.filter(language=language)
        return queryset

    def get_object(self, queryset=None):
        """Return the content object for this URL, tolerating duplicate slugs."""
        if queryset is None:
            queryset = self.get_queryset()

        pk = self.kwargs.get(self.pk_url_kwarg)
        slug = self.kwargs.get(self.slug_url_kwarg)
        if pk is not None:
            queryset = queryset.filter(pk=pk)
        elif slug is not None:
            queryset = queryset.filter(**{self.get_slug_field(): slug})
        else:
            raise AttributeError(
                f"{self.__class__.__name__} must be called with either an object pk or a slug in the URLconf."
            )

        # Two rows are enough to know the lookup is ambiguous.
        matches = list(queryset[:2])
        if not matches:
            raise Http404(f"No {queryset.model._meta.verbose_name} found matching the query")
        if len(matches) > 1:
            logger.error(
                "Ambiguous detail URL for %s: %s=%r%s matches more than one object, "
                "serving pk=%s. A slug has to identify a single object; check for "
                "another object using the same slug.",
                queryset.model._meta.label,
                self.get_slug_field() if slug is not None else "pk",
                slug if slug is not None else pk,
                f" (language={get_language()!r})" if self.has_language_field else "",
                matches[0].pk,
            )
        return matches[0]


class FrontendEditableMixin:
    def get_object(self, queryset=None):
        """Add object to toolbar"""
        obj = super().get_object(queryset)
        try:
            # Add to toolbar if not in endpoint
            self.request.toolbar.set_object(obj)
        except AttributeError:
            pass
        return obj


def custom_detail_view_factory(model: type[models.Model]) -> type[DetailView]:
    # ``FrontendEditableMixin`` wraps the lookup, so it comes first; the resolution
    # itself lives in ``CustomDetailViewMixin`` and replaces ``DetailView``'s.
    return type(
        f"{model.__name__}DetailView",
        (FrontendEditableMixin, CustomDetailViewMixin, DetailView),
        {
            "model": model,
            "grouper_field_name": getattr(model, "_grouper_field_name", None),
        },
    )


def render_frontend_editor(request: HttpRequest, content: models.Model) -> HttpResponse:
    template = content.get_template()
    context = {content._meta.model_name: content}
    return TemplateResponse(request, template, context)
