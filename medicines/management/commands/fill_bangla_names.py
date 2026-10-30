"""Fill empty Bangla names, spelled by sound and marked as automatic. Names already there are kept."""
from django.core.management.base import BaseCommand

from medicines.models import DosageForm, DrugClass, Generic, Manufacturer, Medicine
from medicines.transliterate import form_to_bangla, to_bangla

BATCH_SIZE = 500


class Command(BaseCommand):
    help = "Fill empty Bangla names for medicines, generics, companies, forms and classes."

    def handle(self, *args, **options):
        for model, convert in ((DosageForm, form_to_bangla), (Manufacturer, to_bangla), (Generic, to_bangla), (DrugClass, to_bangla)):
            rows = list(model.objects.filter(name_bn=""))
            for row in rows:
                row.name_bn, row.name_bn_auto = convert(row.name), True
            model.objects.bulk_update(rows, ["name_bn", "name_bn_auto"], batch_size=BATCH_SIZE)
            self.stdout.write(f"{model.__name__}: {len(rows)}")

        # Every medicine's search text includes the names filled in above.
        medicines = list(Medicine.objects.select_related("generic", "dosage_form"))
        filled = 0
        for medicine in medicines:
            if not medicine.brand_name_bn:
                medicine.brand_name_bn, medicine.brand_name_bn_auto = to_bangla(medicine.brand_name), True
                filled += 1
            medicine.search_text = medicine.build_search_text()
        Medicine.objects.bulk_update(medicines, ["brand_name_bn", "brand_name_bn_auto", "search_text"], batch_size=BATCH_SIZE)
        self.stdout.write(self.style.SUCCESS(f"Medicines: {filled} names filled, {len(medicines)} search entries updated."))
