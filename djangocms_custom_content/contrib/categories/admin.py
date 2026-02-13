from django.contrib import admin

from .models import FlatCategory


@admin.register(FlatCategory)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("title", "is_featured")
    list_filter = ("is_featured",)
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "slug")
