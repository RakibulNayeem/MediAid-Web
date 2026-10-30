"""Tick "show on home page" for the well-known medicines in medicines/popular.py."""
from django.core.management.base import BaseCommand

from medicines.models import Medicine
from medicines.popular import POPULAR_MEDICINES
from medicines.text import normalize_strength


class Command(BaseCommand):
    help = "Mark well-known medicines to appear on the home page."

    def handle(self, *args, **options):
        Medicine.objects.filter(is_popular=True).update(is_popular=False)
        total = 0
        for brand, strength, form in POPULAR_MEDICINES:
            # A brand can be registered at several factories; one entry on the home page is enough.
            medicine = Medicine.objects.filter(
                brand_name__iexact=brand, strength_key=normalize_strength(strength), dosage_form__name__iexact=form,
            ).order_by("manufacturer__name").first()
            if medicine:
                Medicine.objects.filter(pk=medicine.pk).update(is_popular=True)
                total += 1
        self.stdout.write(self.style.SUCCESS(f"Marked {total} medicines."))
