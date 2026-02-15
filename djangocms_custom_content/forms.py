from django import forms
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.forms import ModelMultipleChoiceField
from django.utils.encoding import force_str


class GenericM2MFormField(ModelMultipleChoiceField):
    """
    Form field for generic M2M relationships.

    Handles saving and loading of generic M2M relations in forms.
    This field integrates with Django's admin to provide a seamless
    experience for managing generic many-to-many relationships.

    Args:
        ``instance``: The model instance this field is bound to
        ``through_model``: The relation model (inherits from AbstractCustomRelation)
        ``related_field_name``: The field name on the through_model pointing to related objects
        ``queryset``: The queryset of available objects to select from
        ``widget``: The widget to use for rendering (defaults to FilteredSelectMultiple)
        ``**kwargs``: Additional arguments passed to ModelMultipleChoiceField

    Example::

        field = GenericM2MFormField(
            instance=blog_post,
            through_model=PersonRelation,
            related_field_name='instance',
            label='Authors',
            required=False
        )
    """

    def __init__(self, *, instance=None, through_model=None, related_field_name=None, **kwargs):
        self.instance = instance
        self.through_model = through_model
        self.related_field_name = related_field_name

        # Get the related model and queryset
        if through_model and related_field_name:
            related_model = through_model._meta.get_field(related_field_name).related_model
            manager = getattr(related_model, "admin_manager", related_model.objects)
            kwargs["queryset"] = manager.all()

        super().__init__(**kwargs)

    def prepare_value(self, value):
        """Convert current relations to PKs for the widget."""
        if not self.instance or not self.instance.pk or not self.through_model:
            return []

        content_type = ContentType.objects.get_for_model(self.instance)
        relation_pks = self.through_model.objects.filter(
            content_type=content_type, object_id=self.instance.pk
        ).values_list(self.related_field_name, flat=True)

        return list(relation_pks)

    def clean(self, value):
        """Validate the selected objects."""
        if value is None:
            value = []

        if not value and self.required:
            raise forms.ValidationError(self.error_messages["required"])

        # Convert to list if needed
        if not isinstance(value, (list, tuple)):
            value = [value]

        # Filter queryset by the provided PKs
        key = "pk__in"
        try:
            qs = self.queryset.filter(**{key: value})
            # Force evaluation to check if all items exist
            pks = {force_str(getattr(o, "pk")) for o in qs}
        except (ValueError, TypeError):
            raise forms.ValidationError(
                self.error_messages["invalid_choice"],
                code="invalid_choice",
            )

        # Check that all provided values were found
        for val in value:
            if force_str(val) not in pks:
                raise forms.ValidationError(
                    self.error_messages["invalid_choice"],
                    code="invalid_choice",
                    params={"value": val},
                )

        return qs

    def save_relations(self, instance, cleaned_data=None):
        """Save the M2M relations after the main instance is saved.

        Args:
            instance: The model instance to save relations for
            cleaned_data: The cleaned data (list of related objects) from the form
        """
        if not self.instance or not self.instance.pk or not self.through_model:
            return

        if cleaned_data is None:
            return

        content_type = ContentType.objects.get_for_model(self.instance)

        # Get current values
        selected_pks = {obj.pk for obj in cleaned_data}

        # Get existing relations
        existing_relations = self.through_model.objects.filter(content_type=content_type, object_id=self.instance.pk)
        existing_pks = set(existing_relations.values_list(self.related_field_name, flat=True))

        # Remove relations that are no longer selected
        to_remove = existing_pks - selected_pks
        if to_remove:
            existing_relations.filter(**{f"{self.related_field_name}__pk__in": to_remove}).delete()

        # Add new relations
        to_add = selected_pks - existing_pks
        if to_add:
            related_model = self.through_model._meta.get_field(self.related_field_name).related_model
            for pk in to_add:
                related_obj = related_model.objects.get(pk=pk)
                self.through_model.objects.create(
                    content_type=content_type, object_id=self.instance.pk, **{self.related_field_name: related_obj}
                )


class GenericM2MModelForm(forms.ModelForm):
    """
    Base ModelForm that adds GenericM2MFormFields automatically.

    This form class automatically creates form fields for generic M2M relationships
    defined in the model's Meta.generic_m2m_fields attribute. It handles both
    rendering the fields and saving the relations.

    Usage::

        class BlogPostAdminForm(GenericM2MModelForm):
            class Meta:
                model = BlogPost
                fields = '__all__'
                generic_m2m_fields = {
                    'authors': {
                        'through_model': PersonRelation,
                        'related_field_name': 'instance',
                        'label': 'Authors',
                        'help_text': 'Select the authors of this blog post',
                        'required': False,
                    }
                }

        @admin.register(BlogPost)
        class BlogPostAdmin(admin.ModelAdmin):
            form = BlogPostAdminForm

    Attributes:
        Meta.generic_m2m_fields: Dictionary mapping field names to configuration dicts.
            Each config dict can contain:
            - ``through_model``: Required. The relation model class
            - ``related_field_name``: Required. The field name on the relation model
            - ``label``: Optional. The field label
            - ``help_text``: Optional. Help text for the field
            - ``required``: Optional. Whether the field is required (default: False)
            - ``widget``: Optional. Custom widget (default: FilteredSelectMultiple)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add generic M2M fields defined in Meta
        if hasattr(self.Meta, "generic_m2m_fields"):
            for field_name, config in self.Meta.generic_m2m_fields.items():
                # Allow custom widget or use default FilteredSelectMultiple
                widget = config.get("widget")
                if widget is None:
                    widget = admin.widgets.FilteredSelectMultiple(config.get("label", field_name), is_stacked=False)

                self.fields[field_name] = GenericM2MFormField(
                    instance=self.instance,
                    through_model=config["through_model"],
                    related_field_name=config["related_field_name"],
                    label=config.get("label", field_name),
                    help_text=config.get("help_text", ""),
                    required=config.get("required", False),
                    widget=widget,
                )

    def save(self, commit=True):
        """Save the instance and handle generic M2M relations."""
        instance = super().save(commit=commit)

        if commit and hasattr(self.Meta, "generic_m2m_fields"):
            # Save M2M relations after instance is saved
            for field_name in self.Meta.generic_m2m_fields.keys():
                if field_name in self.fields and field_name in self.cleaned_data:
                    self.fields[field_name].save_relations(instance, self.cleaned_data[field_name])

        return instance
