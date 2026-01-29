from django.contrib import admin

from .models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("title", "is_featured")
    list_filter = ("is_featured",)
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title",)
