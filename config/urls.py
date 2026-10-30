from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),  # the language toggle posts here
    path("medicines/", include("medicines.urls")),
    path("emergency/", include("emergency.urls")),
    path("", include("core.urls")),
]
