from django.conf import settings
from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
]
if settings.ACCOUNTS_ENABLED:
    urlpatterns.append(path("profile/", views.profile, name="profile"))
