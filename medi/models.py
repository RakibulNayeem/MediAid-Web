from os import name
# from django.contrib.auth import default_app_config
from django.db import models
from django.db.models.fields import *


class Zilla(models.Model):
    name=models.CharField(max_length=100)
    def __str__(self):
        return self.name


class BloodGroup(models.Model):
    name = models.CharField(max_length=20)
    def __str__(self):
        return self.name


# Create your models here.
class bloodDonor(models.Model):
    donor_id = models.AutoField
    donor_name = models.CharField(max_length=50)
    address = models.CharField(max_length=300)
    blood_group = models.ForeignKey(BloodGroup, null=True, blank=True, on_delete=models.CASCADE)
    zilla = models.ForeignKey(Zilla, null=True, blank=True, on_delete=models.CASCADE)
    contact = models.CharField(max_length=20)
    last_donation_date = models.DateField()
    def __str__(self):
        return self.donor_name



# Area
class Area(models.Model):
    name=models.CharField(max_length=100)
    zilla=models.ForeignKey(Zilla,on_delete=models.CASCADE, related_name='areas')
    def __str__(self):
        return self.name


class Speciality(models.Model):
    name = models.CharField(max_length=40)

    def __str__(self):
        return self.name
 

# Doctors model
class Doctors(models.Model):
    doctor_id = models.AutoField
    name = models.CharField(max_length=60)
    degree = models.CharField(max_length=100)
    hospital = models.CharField(max_length=100)
    speciality = models.ForeignKey(Speciality,  null=True, blank=True, on_delete=models.CASCADE)
    chamber_address = models.CharField(max_length=100)
    open_time = models.TimeField()
    close_time = models.TimeField()
    active_days = models.CharField(max_length=100)
    zilla = models.ForeignKey(Zilla, null=True, blank=True, on_delete=models.CASCADE)
    upazila = models.CharField(max_length=25)
    contact = models.CharField(max_length=20)

    def __str__(self):
        return self.name


# type
class AmbulanceType(models.Model):
    id = models.AutoField
    name = models.CharField(default='', max_length=30)

    def __str__(self):
        return self.name


# Ambulance 
class Ambulance(models.Model):
    id = models.AutoField
    name = models.CharField(default='', max_length=100)
    address = models.CharField(default='', max_length=100)
    type = models.ForeignKey(AmbulanceType, null=True, blank=True, on_delete=models.CASCADE)
    vehicle_no = models.CharField(default='', max_length=25)
    upazila = models.CharField(default='', max_length=25)
    zilla = models.ForeignKey(Zilla, null=True, blank=True, on_delete=models.CASCADE)
    contact = models.CharField(default='', max_length=20)

    def __str__(self):
        return self.name

# Blood Bank Category
class BBCategory(models.Model):
    id = models.AutoField
    name = models.CharField(default='', max_length=30)

    def __str__(self):
        return self.name

# Blood Bank
class BloodBank(models.Model):
    id = models.AutoField
    name = models.CharField(default='', max_length=100)
    address = models.CharField(default='', max_length=100)
    open = models.CharField(default='', max_length=100)
    category = models.ForeignKey(BBCategory, null=True, blank=True, on_delete=models.CASCADE)
    upazila = models.CharField(default='', max_length=25)
    zilla = models.ForeignKey(Zilla, null=True, blank=True, on_delete=models.CASCADE)
    contact = models.CharField(default='', max_length=20)

    def __str__(self):
        return self.name

# Hospital Category
class Category(models.Model):
    id = models.AutoField
    name = models.CharField(default='', max_length=30)

    def __str__(self):
        return self.name

 # Hospital model
class Hospital(models.Model):
    id = models.AutoField
    name = models.CharField(default='', max_length=100)
    address = models.CharField(default='', max_length=100)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.CASCADE)
    upazila = models.CharField(default='', max_length=25)
    zilla = models.ForeignKey(Zilla, null=True, blank=True, on_delete=models.CASCADE)
    contact = models.CharField(default='', max_length=20)

    def __str__(self):
        return self.name


# Services

class Our_Services(models.Model):
    id = models.AutoField
    name = models.CharField(default='', max_length=30)
    image = models.ImageField(upload_to='medi/images', default = '')

    def __str__(self):
      return self.name