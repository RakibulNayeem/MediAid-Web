from django.urls import path

from . import views

app_name = "emergency"

urlpatterns = [
    path("", views.hub, name="hub"),
    path("<slug:section>/", views.section, name="section"),
]
