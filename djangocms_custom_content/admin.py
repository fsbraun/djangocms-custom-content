from cms.utils.urlutils import admin_reverse
from django.http import HttpResponseRedirect
from django.urls import path


class CustomGrouperAdminMixin:
    def get_urls(self):
        urls = super().get_urls()

        info = f"{self.content_model._meta.app_label}_{self.content_model._meta.model_name}"
        return [
            path("breadcrumb_redir/<slug>/", self.admin_site.admin_view(self.breadcrumb_redir), name=f"{info}_change"),
            path("breadcrumb_redir/", self.admin_site.admin_view(self.breadcrumb_redir), name=f"{info}_changelist"),
        ] + urls

    def breadcrumb_redir(self, request, *args, **kwargs):
        print(args, kwargs)
        id = kwargs.get("slug")
        info = f"{self.model._meta.app_label}_{self.model._meta.model_name}"
        print(info)
        if id and False:
            return HttpResponseRedirect(admin_reverse(f"{info}_change", args=(id,)))
        return HttpResponseRedirect(admin_reverse(f"{info}_changelist"))
