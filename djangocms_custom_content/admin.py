from cms.utils.urlutils import admin_reverse
from django.apps import apps
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Prefetch
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import path

from .models import GenericM2MDescriptor, InverseRelationDescriptor


class CustomGrouperAdminMixin:
    """Admin mixin to optimize queries and redirect content endpoints.

    This mixin prefetches related content for admin lists and provides a
    breadcrumb redirect compatible with django CMS versioning.
    """

    def get_queryset(self, request: HttpRequest):
        """Return a queryset prefetched with latest related content.

        Args:
            ``request``: The current admin request.

        Returns:
            The queryset, optionally prefetched with admin manager content.
        """
        qs = super().get_queryset(request)
        content_model = getattr(self, "content_model", None)
        if content_model is None:
            return qs

        grouper_fk_field = next(
            (
                f
                for f in content_model._meta.get_fields()
                if isinstance(f, models.ForeignKey) and f.related_model is self.model
            ),
            None,
        )
        if grouper_fk_field is None:
            return qs
        accessor_name = grouper_fk_field.remote_field.get_accessor_name()
        manager = content_model._meta.managers_map.get("admin_manager", content_model._default_manager)
        prefetch = Prefetch(accessor_name, queryset=manager.latest_content(), to_attr="_admin_prefetch_cache")

        return qs.prefetch_related(prefetch)

    def get_urls(self):
        """Register breadcrumb redirect URLs for grouper admin views."""
        urls = super().get_urls()

        info = f"{self.content_model._meta.app_label}_{self.content_model._meta.model_name}"
        return [
            path("breadcrumb_redir/<slug>/", self.admin_site.admin_view(self.breadcrumb_redir), name=f"{info}_change"),
            path("breadcrumb_redir/", self.admin_site.admin_view(self.breadcrumb_redir), name=f"{info}_changelist"),
        ] + urls

    def breadcrumb_redir(self, request, *args, **kwargs):
        """Redirect versioning breadcrumb URLs to the grouper admin.

        djangocms-versioning uses content admin URLs for breadcrumbs, but this
        project uses grouper admin classes and must redirect accordingly.
        """
        id = kwargs.get("slug")
        info = f"{self.model._meta.app_label}_{self.model._meta.model_name}"
        if id:
            config = apps.get_app_config("djangocms_custom_content").cms_config
            if self.model in config.cms_toolbar_enabled_models:
                # Redirect to the change view in the toolbar modal
                grouper_model = config.custom_content_groupers[self.model][0]
                info = f"{grouper_model._meta.app_label}_{grouper_model._meta.model_name}"
                return HttpResponseRedirect(admin_reverse(f"{info}_change", args=(id,)))
        return HttpResponseRedirect(admin_reverse(f"{info}_changelist"))


class GenericM2MAdminMixin:
    """
    Mixin for ModelAdmin classes to support generic M2M relations.

    This mixin adds prefetch optimization for generic M2M relationships
    in admin list views, improving performance when displaying related objects.

    Usage::

        @admin.register(BlogPost)
        class BlogPostAdmin(GenericM2MAdminMixin, admin.ModelAdmin):
            form = BlogPostAdminForm  # Form with generic_m2m_fields
            list_display = ['title', 'get_authors']
            list_filter = ['created']
            generic_m2m_fields = ['authors']  # Specify fields to optimize

            def get_authors(self, obj):
                return ", ".join(str(a) for a in obj.authors.all())
            get_authors.short_description = 'Authors'

    Attributes:
        generic_m2m_fields: List of field names that are generic M2M relations.
            These will be prefetched in the queryset for list views.
    """

    generic_m2m_fields = []

    def get_queryset(self, request):
        """Prefetch generic M2M relations for optimized list views."""
        qs = super().get_queryset(request)

        # Prefetch generic M2M relations for better performance
        for field_name in self.generic_m2m_fields:
            # Get the descriptor from the model
            descriptor = getattr(self.model, field_name, None)
            if isinstance(descriptor, (GenericM2MDescriptor, InverseRelationDescriptor)):
                relation_model = descriptor.relation_model

                # Check if the reverse relation exists
                reverse_accessor = None
                for field in self.model._meta.get_fields():
                    if hasattr(field, "related_model") and field.related_model == relation_model:
                        reverse_accessor = field.get_accessor_name()
                        break

                if reverse_accessor:
                    qs = qs.prefetch_related(
                        Prefetch(reverse_accessor, queryset=relation_model.objects.select_related("content_type"))
                    )

        return qs


class GenericM2MListFilter(admin.SimpleListFilter):
    """
    Custom list filter for generic M2M relationships.

    This filter allows filtering admin lists by related objects in a
    generic M2M relationship. It automatically queries the available
    related objects and creates filter options.

    Usage::

        class AuthorFilter(GenericM2MListFilter):
            title = 'Author'
            parameter_name = 'author'
            relation_model = PersonRelation
            related_field = 'instance'

        @admin.register(BlogPost)
        class BlogPostAdmin(admin.ModelAdmin):
            list_filter = [AuthorFilter, 'created']

    Attributes:
        relation_model: The relation model (inherits from AbstractCustomRelation)
        related_field: The field name on the relation model pointing to related objects
        title: The filter title displayed in the admin
        parameter_name: The URL parameter name for this filter
    """

    relation_model = None  # Set to your relation model
    related_field = "instance"  # Field name on relation model

    def lookups(self, request, model_admin):
        """Return list of tuples for filter choices."""
        if not self.relation_model:
            return []

        related_model = self.relation_model._meta.get_field(self.related_field).related_model
        manager = getattr(related_model, "admin_manager", related_model.objects)

        # Limit to 100 for performance, but could be made configurable
        return [(obj.pk, str(obj)) for obj in manager.all()[:100]]

    def queryset(self, request, queryset):
        """Filter the queryset based on selected value."""
        if self.value():
            ct = ContentType.objects.get_for_model(queryset.model)
            return queryset.filter(
                pk__in=self.relation_model.objects.filter(
                    **{
                        f"{self.related_field}__pk": self.value(),
                        "content_type": ct,
                    }
                ).values_list("object_id", flat=True)
            )
        return queryset
