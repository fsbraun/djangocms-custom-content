from django.apps import apps
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import models
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.template.response import TemplateResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import DetailView

from djangocms_custom_content.helpers import get_custom_config


class CustomDetailViewMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.grouper_field_name = get_custom_config(self.model)[1]

    def get_queryset(self):
        """Override the default queryset to prefetch content for the grouper."""
        return super().get_queryset().select_related(self.grouper_field_name)


class FrontendEditableMixin:
    def get_object(self):
        """Add object to toolbar"""
        obj = super().get_object()
        try:
            # Add to toolbar if not in endpoint
            self.request.toolbar.set_object(obj)
        except AttributeError:
            pass
        return obj


def custom_detail_view_factory(model: type[models.Model]) -> type[DetailView]:
    return type(
        f"{model.__name__}DetailView",
        (CustomDetailViewMixin, FrontendEditableMixin, DetailView),
        {
            "model": model,
            "grouper_field_name": getattr(model, "_grouper_field_name", None),
        },
    )


def render_frontend_editor(request: HttpRequest, content: models.Model) -> HttpResponse:
    template = content.get_template()
    context = {content._meta.model_name: content}
    return TemplateResponse(request, template, context)


@method_decorator(staff_member_required, name="dispatch")
class CustomM2MAutocompleteView(View):
    """JSON autocomplete endpoint for ``CMSConfig.m2m`` admin widgets.

    Looks up the target model by ``app_label`` + ``model_name`` query params
    and uses its registered ``ModelAdmin`` (``get_queryset`` +
    ``get_search_results``) to apply permission filtering and search.
    """

    paginate_by = 20

    def get(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        app_label = request.GET.get("app_label")
        model_name = request.GET.get("model_name")
        if not (app_label and model_name):
            raise Http404("Missing target identifiers")
        try:
            target_model = apps.get_model(app_label, model_name)
        except LookupError as exc:
            raise Http404("Unknown target model") from exc

        target_admin = admin.site._registry.get(target_model)
        if target_admin is None:
            raise PermissionDenied("Target model is not registered with admin")

        term = request.GET.get("term", "")
        qs = target_admin.get_queryset(request)
        qs, _may_have_duplicates = target_admin.get_search_results(request, qs, term)

        paginator = Paginator(qs, self.paginate_by)
        page = paginator.get_page(request.GET.get("page", 1))
        return JsonResponse(
            {
                "results": [{"id": str(obj.pk), "text": str(obj)} for obj in page.object_list],
                "pagination": {"more": page.has_next()},
            }
        )
