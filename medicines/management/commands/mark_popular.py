"""Tick "show on home page" for the well-known medicines in medicines/popular.py."""
from django.core.management.base import BaseCommand

from medicines.models import Medicine
from medicines.popular import POPULAR_MEDICINES
from medicines.text import normalize_strength


class Command(BaseCommand):
    help = "Mark well-known medicines to appear on the home page."

    def handle(self, *args, **options):
        total = 0
        for brand, strength, form in POPULAR_MEDICINES:
            total += Medicine.objects.filter(
                brand_name__iexact=brand, strength_key=normalize_strength(strength), dosage_form__name__iexact=form,
            ).update(is_popular=True)
        self.stdout.write(self.style.SUCCESS(f"Marked {total} medicines."))
