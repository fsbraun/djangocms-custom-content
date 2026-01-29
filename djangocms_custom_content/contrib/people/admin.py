from django.contrib import admin

from .models import Person


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ("name", "role")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "role", "bio")
