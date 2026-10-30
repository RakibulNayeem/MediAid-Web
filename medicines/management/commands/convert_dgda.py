"""Turn DGDA's "Export All to Excel (CSV)" file into the format `import_csv medicines` reads.

Get the file from DGDA's Medicine Information page, linked from dgda.gov.bd. Usage:
    python manage.py convert_dgda medicine_information_export.csv dgda_medicines.csv
    python manage.py import_csv medicines dgda_medicines.csv --dry-run
"""
import csv
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from medicines.text import normalize, normalize_strength

# Materials for factories and products for animals, not medicines people buy.
EXCLUDED_FORMS = {"raw materials", "liter", "kg", "bolus", "water soluble powder", "pellets"}
# "Vitamin B1 + Zinc 5 mg + 2 mg" -> "Vitamin B1 + Zinc", "5 mg + 2 mg". A strength is a separate word
# that starts with a number and goes on to a unit, so the "1" in "B1" doesn't count.
GENERIC_AND_STRENGTH = re.compile(r"^(.*?)\s+(\.?\d[\d.,/]*\s*(?:%|[a-zA-Zµ]+|\+).*)$")
OUTPUT_COLUMNS = ["brand_name", "generic", "strength", "dosage_form", "manufacturer", "dgda_registration_no"]


def convert_rows(rows):
    """Returns (converted rows, {reason: number of rows skipped})."""
    converted, seen, registrations = [], set(), set()
    skipped = {"missing details": 0, "no strength": 0, "not for people": 0, "duplicate": 0}
    for row in rows:
        brand = row["Trade Name"].strip()
        generic_text = " ".join(row["Generic Name With Strength"].split())
        form = row["Dosage Form"].strip()
        maker = row["Company"].strip()
        registration = row["DAR No"].strip()
        if not (brand and generic_text and form and maker):
            skipped["missing details"] += 1
            continue
        if form.lower() in EXCLUDED_FORMS or "(api)" in brand.lower():
            skipped["not for people"] += 1
            continue
        match = GENERIC_AND_STRENGTH.match(generic_text)
        if not match:
            skipped["no strength"] += 1
            continue
        generic, strength = match.groups()
        key = (normalize(brand), normalize_strength(strength), normalize(form), normalize(maker))
        if key in seen:
            skipped["duplicate"] += 1
            continue
        seen.add(key)
        # A few DAR numbers appear on different products. Keep each product, but only one can hold the number.
        if registration in registrations:
            registration = ""
        registrations.add(registration)
        item = {
            "brand_name": brand, "generic": generic, "strength": strength, "dosage_form": form,
            "manufacturer": maker, "dgda_registration_no": registration,
        }
        if row.get("link"):
            item["dgda_link"] = row["link"]  # the price page, used by fetch_dgda_prices
        converted.append(item)
    return converted, skipped


class Command(BaseCommand):
    help = "Convert DGDA's medicine export into MediAid's import format."

    def add_arguments(self, parser):
        parser.add_argument("source")
        parser.add_argument("output")

    def handle(self, *args, **options):
        source = Path(options["source"])
        if not source.is_file():
            raise CommandError(f"File not found: {source}")
        with source.open(encoding="utf-8-sig", newline="") as file:
            try:
                converted, skipped = convert_rows(csv.DictReader(file))
            except KeyError as exc:
                raise CommandError(f"This isn't a DGDA export: column {exc} is missing.")
        with open(options["output"], "w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, OUTPUT_COLUMNS)
            writer.writeheader()
            writer.writerows(converted)
        self.stdout.write(self.style.SUCCESS(f"Wrote {len(converted)} medicines to {options['output']}."))
        for reason, count in skipped.items():
            self.stdout.write(f"Skipped, {reason}: {count}")
