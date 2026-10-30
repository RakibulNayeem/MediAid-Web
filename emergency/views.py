from django.http import Http404
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _

# Phase 2 replaces these placeholders with real listings.
SECTIONS = {
    "blood": _("Find blood"),
    "ambulance": _("Ambulance"),
    "hospital": _("Hospital"),
    "doctor": _("Doctor"),
}


def hub(request):
    return render(request, "emergency/coming_soon.html", {"title": _("Emergency services")})


def section(request, section):
    if section not in SECTIONS:
        raise Http404
    return render(request, "emergency/coming_soon.html", {"title": SECTIONS[section]})
