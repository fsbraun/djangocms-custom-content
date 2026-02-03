from django.db import models
from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from django.views.generic import DetailView


class CustomDetailViewMixin:
    pass


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
        (CustomDetailViewMixin, DetailView),
        {
            "model": model,
        },
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
    context = {"instance": content}
    return TemplateResponse(request, template, context)
