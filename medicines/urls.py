from django.urls import path

from . import views

app_name = "medicines"

urlpatterns = [
    path("search/", views.search, name="search"),
    path("generics/", views.generic_list, name="generic_list"),
    path("generics/<slug:slug>/", views.generic_detail, name="generic_detail"),
    path("manufacturers/", views.manufacturer_list, name="manufacturer_list"),
    path("manufacturers/<slug:slug>/", views.manufacturer_detail, name="manufacturer_detail"),
    path("classes/", views.drug_class_list, name="drug_class_list"),
    path("classes/<slug:slug>/", views.drug_class_detail, name="drug_class_detail"),
    path("<slug:slug>/", views.medicine_detail, name="medicine_detail"),
]
