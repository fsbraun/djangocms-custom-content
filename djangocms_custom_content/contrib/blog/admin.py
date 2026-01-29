from django.contrib import admin

from .models import BlogPost


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "published_at", "is_featured")
    list_filter = ("is_featured", "published_at")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "excerpt", "body")
