from django.urls import path
from django.urls.resolvers import URLPattern
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.index, name= 'home'),
    path('login/', views.loginPage, name= 'login'),
    path('logout/', views.logoutUser, name= 'logout'),
    path('register/', views.registerPage, name= 'register'),
    path('account/', views.userAccount, name= 'userAccount'),
    path('about/', views.about, name= 'AboutUs'),
    path('terms/', views.TermsConditions, name= 'Terms'),
    path('contact/', views.contact, name= 'ContactUs'),
    path('index/', views.our_services, name= 'ourServices'),
    path('doctor/', views.doctor, name= 'Doctor'),
    path('hospital/', views.hospital, name= 'Hospital'), 
    path('ambulance/', views.ambulance, name= 'Ambulance'),
    path('blooddonor/', views.blood_Donor, name= 'BloodDonor'),
    path('bloodbank/', views.bloodBank, name= 'BloodBank'),
    path('healthtips/', views.healthTips, name= 'HealthTips'),
    path('facts/', views.facts, name= 'Facts'),
    path('load-area/', views.load_area, name='ajax_load_area'),
    path('shimul/', views.shimul, name='shimul'),

] + static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)