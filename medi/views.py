import django
from django.db.models import query
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.db.models import Q
from .models import *
import json
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group

from django.contrib.auth.forms import UserCreationForm
from .forms import CreateUserForm
from django.contrib import messages
from .decorators import unauthenticated_user, allowed_users
from .filters import *


def index(request):
    return render(request, 'medi/index.html')


@unauthenticated_user
def registerPage(request): 
    form = CreateUserForm()
    if request.method == 'POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')

            group = Group.objects.get(name = 'customer')
            user.groups.add((group))

            messages.success(request, 'Account was created for ' + username)
            return redirect('login')


    params = {'form': form}
    return render(request, 'medi/register.html', params)


@unauthenticated_user
def loginPage(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username= username, password = password)

        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.info(request, 'Username OR password is incorrect!')
   
    params = {}

    return render(request, 'medi/login.html', params)


# User Account Dashboard
@login_required(login_url='login')
# @allowed_users(allowed_roles=['admin'])
def userAccount(request):
    
    return render(request, 'medi/account.html')


# Logout user
def logoutUser(request):
    logout(request)
    return redirect('home')


def about(request):
    return render(request, 'medi/about_us.html')



def TermsConditions(request):
    return render(request, 'medi/terms_condition.html')


def contact(request):
    return render(request, 'medi/contact_us.html')

# Services
def our_services(request):
    services = Our_Services.objects.all().order_by('name')

   # Passing parameters 
    params = {
        'services': services,
        }

    return render(request, 'medi/index.html', params)


# Blood Donor search function

def blood_Donor(request):    
    #blood donor list after filter
    gr = request.GET.get('group', None)
   
    if gr:
        donors = bloodDonor.objects.filter(blood_group=gr)
    else:
        donors = bloodDonor.objects.all()

    donors_filter = donorFilter(request.GET, queryset=donors)

    blood_group = BloodGroup.objects.all().order_by('name')

    # paginator = Paginator(donors_filter, per_page=3)
    # page_number = request.GET.get('page',1)
    # page_obj = paginator.get_page(page_number)

   # Passing parameters 
    params = {
        'donors' : donors_filter,
        'blood_group':blood_group,
        # 'paginator': paginator,
        # 'page_number': int(page_number),
        }

    return render(request, 'medi/blood_donor.html', params)

def shimul(request):
    gr = request.GET.get('group', None)
    if gr:
        donors = bloodDonor.objects.filter(blood_group=gr)
    else:
        donors = bloodDonor.objects.all()
    donors_filter = donorFilter(request.GET, queryset=donors)
    blood_group = BloodGroup.objects.all().order_by('name')
    context = {
        'donors' : donors_filter,
        'blood_group':blood_group,
    }
    return render(request, 'medi/shimul.html', context)

# Load area for every zilla in search box.
def load_area(request):
    zilla_id = request.GET.get('zilla')
    area = Area.objects.filter(zilla_id=zilla_id).order_by('name')
    return render(request, 'medi/area_dropdown_list.html', {'area': area})



# Doctor search function
def doctor(request):
    gr = request.GET.get('group', None)
    if gr:
        doctors = Doctors.objects.filter(speciality=gr)
    else:
        doctors = Doctors.objects.all()
    doctors_filter = doctorFilter(request.GET, queryset=doctors)
    speciality = Speciality.objects.all().order_by('name')

    context = {
        'doctors' : doctors_filter,
        'speciality':speciality,
    }

#     zilla = Zilla.objects.all().order_by('name')
#     speciality = Speciality.objects.all().order_by('name')
    
#     #blood donor list after filter
#     if 'query' in request.GET:
#         query = request.GET['query']
#         multiple_q = Q(Q(name__icontains=query) | Q(chamber_address__icontains=query) | Q(degree__icontains=query)
#                        | Q(zilla__icontains=query) | Q(contact__icontains=query) | Q(hospital__icontains=query)
#                        | Q(speciality__icontains=query) | Q(open_time__icontains=query) | Q(close_time__icontains=query)
#                        | Q(active_days__icontains=query) | Q(upazila__icontains=query))

#         doctors = Doctors.objects.filter(multiple_q)
#     else:
#         doctors = Doctors.objects.all()

#     paginator = Paginator(doctors, per_page=3)
#     page_number = request.GET.get('page',1)
#     page_obj = paginator.get_page(page_number)

#    # Passing parameters 
#     params = {
#         'doctors': page_obj.object_list,
#         'zilla': zilla,
#         'speciality':speciality,
#         'paginator': paginator,
#         'page_number': int(page_number),
#         }

    return render(request, 'medi/doctor.html', context)


def hospital(request):

    category = Category.objects.all().order_by('name')
    
    #hospital list after filter
    gr = request.GET.get('group', None)
    if gr:
        hospital = Hospital.objects.filter(category=gr)
    else:
        hospital = Hospital.objects.all()

    hospital_filter = hospitalFilter(request.GET, queryset=hospital)

    context = {
        'hospitals' : hospital_filter,
        'category':category,
    }

    return render(request, 'medi/hospital.html', context)


def ambulance(request):
     
    type = AmbulanceType.objects.all().order_by('name')
    
    #blood donor list after filter
    gr = request.GET.get('group', None)
    if gr:
        ambulance = Ambulance.objects.filter(type = gr)
    else:
        ambulance = Ambulance.objects.all()

    ambulance_filter = ambulanceFilter(request.GET, queryset=ambulance)

    context = {
        'ambulance' : ambulance_filter,
        'type':type,
    }


    return render(request, 'medi/ambulance.html', context)


def bloodBank(request):

    bb_category = BBCategory.objects.all().order_by('name')
    
    #hospital list after filter
    gr = request.GET.get('group', None)
    if gr:
        blood_bank = BloodBank.objects.filter(category=gr)
    else:
        blood_bank = BloodBank.objects.all()

    blood_bank_filter = bloodBankFilter(request.GET, queryset=blood_bank)

    context = {
        'blood_banks' : blood_bank_filter,
        'category':bb_category,
    }

    return render(request, 'medi/blood_bank.html',context)


def facts(request):
    return render(request, 'medi/facts.html')


def healthTips(request):
    return render(request, 'medi/health_tips.html')
