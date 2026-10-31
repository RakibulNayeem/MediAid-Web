from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _


class ProfileForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ["first_name", "last_name"]
        labels = {"first_name": _("First name"), "last_name": _("Last name")}
