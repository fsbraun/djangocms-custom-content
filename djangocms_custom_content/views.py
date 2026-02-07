from django.db import models
from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
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
        }
    )


def frontend_view_factory(model: type[models.Model]) -> type[DetailView]:
    return type(
        f"{model.__name__}DetailView",
        (CustomDetailViewMixin, FrontendEditableMixin, DetailView),
        {
            "model": model,
        },
    )


def render_frontend_editor(request: HttpRequest, content: models.Model) -> HttpResponse:
    template = content.get_template()
    context = {content._meta.model_name: content}
    return TemplateResponse(request, template, context)
