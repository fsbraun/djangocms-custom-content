from django.contrib import admin

from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("title", "is_featured")
    list_filter = ("is_featured",)
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "summary", "description")
