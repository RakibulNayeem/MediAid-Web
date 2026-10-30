from django.conf import settings
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "MediAid admin"
admin.site.site_title = "MediAid admin"
admin.site.index_title = "Manage MediAid"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),  # the language toggle posts here
    path("medicines/", include("medicines.urls")),
    path("emergency/", include("emergency.urls")),
    path("", include("core.urls")),
]
if settings.ACCOUNTS_ENABLED:
    urlpatterns.insert(0, path("accounts/", include("allauth.urls")))
