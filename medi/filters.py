from .models import Ambulance, BloodBank, bloodDonor, Doctors, Hospital
import django_filters
from django.shortcuts import render, redirect

class donorFilter(django_filters.FilterSet):
    # address = django_filters.CharFilter(lookup_expr='icontains')
    class Meta:
        model = bloodDonor
        fields = ['blood_group', 'zilla', ]


class doctorFilter(django_filters.FilterSet):
   # name = django_filters.CharFilter(lookup_expr='icontains')
    
    class Meta:
        model = Doctors
        fields = ['speciality', 'zilla', ]

class hospitalFilter(django_filters.FilterSet):
    
    class Meta:
        model = Hospital
        fields = ['category', 'zilla', ]


class bloodBankFilter(django_filters.FilterSet):
    
    class Meta:
        model = BloodBank
        fields = ['category', 'zilla', ]

class ambulanceFilter(django_filters.FilterSet):
    
    class Meta:
        model = Ambulance
        fields = ['type', 'zilla', ]