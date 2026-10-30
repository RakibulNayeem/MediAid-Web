"""CSV import for medicines and generic information. Used by the admin page and `manage.py import_csv`.

Nothing is saved unless the whole file is valid, so a bad row can't leave half an import behind.
Empty optional cells keep what's already stored, so a price-only update can't wipe other data.
"""
import csv
import io
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation

from django.db import connection, transaction
from django.utils.text import slugify

from .models import DosageForm, DrugClass, Generic, Manufacturer, Medicine
from .text import normalize, normalize_strength

MEDICINE_REQUIRED = ["brand_name", "generic", "strength", "dosage_form", "manufacturer"]
MEDICINE_COLUMNS = MEDICINE_REQUIRED + [
    "brand_name_bn", "generic_bn", "dosage_form_bn", "manufacturer_bn", "drug_class", "drug_class_bn",
    "price", "price_unit", "price_updated_on", "dgda_registration_no",
]
GENERIC_REQUIRED = ["generic"]
GENERIC_COLUMNS = GENERIC_REQUIRED + [
    "generic_bn", "drug_class", "drug_class_bn", "uses", "how_to_take", "side_effects", "warnings", "source",
]
MAX_ERRORS_SHOWN = 50
BATCH_SIZE = 500
UPDATE_FIELDS = [
    "brand_name", "brand_name_bn", "generic_id", "strength", "dosage_form_id", "manufacturer_id", "price", "price_unit",
    "price_updated_on", "dgda_registration_no", "is_sample", "strength_key", "search_text",
]
MAX_LENGTHS = {
    "brand_name": 200, "brand_name_bn": 200, "generic": 200, "generic_bn": 200, "dosage_form": 200, "dosage_form_bn": 200,
    "manufacturer": 200, "manufacturer_bn": 200, "drug_class": 200, "drug_class_bn": 200, "strength": 100,
    "price_unit": 50, "dgda_registration_no": 100, "source": 300,
}


@dataclass
class ImportResult:
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    errors: list = field(default_factory=list)
    dry_run: bool = False

    @property
    def ok(self):
        return not self.errors


class _Rollback(Exception):
    pass


def _read_rows(data, required, known):
    """Returns (rows, error). Rows are (line_number, {column: stripped value})."""
    if isinstance(data, bytes):
        try:
            data = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            return [], "The file is not UTF-8. In Excel choose: Save As -> CSV UTF-8."
    reader = csv.DictReader(io.StringIO(data.lstrip("\ufeff"), newline=""))
    try:
        columns = [(c or "").strip() for c in reader.fieldnames or []]
        reader.fieldnames = columns
        missing = [c for c in required if c not in columns]
        if missing:
            return [], f"Missing columns: {', '.join(missing)}"
        unknown = [c for c in columns if c not in known]
        if unknown:
            return [], f"Unknown columns: {', '.join(unknown)}"
        rows = [
            (reader.line_num, {k: (v or "").strip() for k, v in row.items() if k})
            for row in reader
            if any((v or "").strip() for v in row.values() if isinstance(v, str))
        ]
    except csv.Error as exc:
        return [], f"This doesn't look like a valid CSV file: {exc}"
    return rows, None


def _too_long(row):
    return [f"{c} is longer than {limit} characters" for c, limit in MAX_LENGTHS.items() if len(row.get(c, "")) > limit]


class _Lookup:
    """Finds or creates Manufacturer / Generic / ... rows, once each, ignoring upper/lower case."""

    def __init__(self, model):
        self.model = model
        self.by_name = {normalize(obj.name): obj for obj in model.objects.all()}

    def get(self, name, name_bn=""):
        key = normalize(name)
        obj = self.by_name.get(key)
        if obj is None:
            obj = self.model.objects.create(name=name, name_bn=name_bn)
            self.by_name[key] = obj
        elif name_bn and obj.name_bn != name_bn:
            obj.name_bn = name_bn
            obj.save(update_fields=["name_bn"])  # a Generic also refreshes its medicines' search text
        return obj


def _medicine_key(brand, strength, form_id, manufacturer_id):
    return (normalize(brand), normalize_strength(strength), form_id, manufacturer_id)


def import_medicines(data, dry_run=False):
    result = ImportResult(dry_run=dry_run)
    rows, error = _read_rows(data, MEDICINE_REQUIRED, MEDICINE_COLUMNS)
    if error:
        result.errors.append(error)
        return result

    try:
        with transaction.atomic():
            _import_medicine_rows(rows, result)
            if dry_run or result.errors:
                raise _Rollback
    except _Rollback:
        return result
    if connection.vendor == "postgresql":
        # Tells PostgreSQL the table changed, so searches use the trigram index straight away.
        with connection.cursor() as cursor:
            cursor.execute("ANALYZE medicines_medicine")
    return result


def _parse_price(text):
    price = Decimal(text.replace(",", ""))
    if not price.is_finite() or price < 0 or price >= Decimal("100000000"):
        raise InvalidOperation
    return price.quantize(Decimal("0.01"))


def _import_medicine_rows(rows, result):
    forms, makers, generics, classes = _Lookup(DosageForm), _Lookup(Manufacturer), _Lookup(Generic), _Lookup(DrugClass)
    existing = list(Medicine.objects.all())
    by_key = {_medicine_key(m.brand_name, m.strength, m.dosage_form_id, m.manufacturer_id): m for m in existing}
    by_reg = {m.dgda_registration_no: m for m in existing if m.dgda_registration_no}
    used_slugs = set(Medicine.objects.values_list("slug", flat=True))
    to_create, to_update, seen, seen_registration = [], {}, {}, {}

    for line, row in rows:
        problems = [f"{c} is empty" for c in MEDICINE_REQUIRED if not row.get(c)] + _too_long(row)
        price = updated_on = None
        if row.get("price"):
            try:
                price = _parse_price(row["price"])
            except InvalidOperation:
                problems.append(f"price '{row['price']}' is not a valid number")
        if row.get("price_updated_on"):
            try:
                updated_on = date.fromisoformat(row["price_updated_on"])
            except ValueError:
                problems.append(f"price_updated_on '{row['price_updated_on']}' must look like 2026-10-30")
        if problems:
            result.errors.append(f"Line {line}: {'; '.join(problems)}")
            continue

        form = forms.get(row["dosage_form"], row.get("dosage_form_bn", ""))
        maker = makers.get(row["manufacturer"], row.get("manufacturer_bn", ""))
        generic = generics.get(row["generic"], row.get("generic_bn", ""))
        if row.get("drug_class"):
            drug_class = classes.get(row["drug_class"], row.get("drug_class_bn", ""))
            if generic.drug_class_id != drug_class.pk:
                generic.drug_class = drug_class
                Generic.objects.filter(pk=generic.pk).update(drug_class=drug_class)

        key = _medicine_key(row["brand_name"], row["strength"], form.pk, maker.pk)
        if key in seen:
            result.errors.append(f"Line {line}: same medicine as line {seen[key]}")
            continue
        seen[key] = line

        registration = row.get("dgda_registration_no") or None
        if registration:
            if registration in seen_registration:
                result.errors.append(f"Line {line}: same DGDA registration no. as line {seen_registration[registration]}")
                continue
            seen_registration[registration] = line
        medicine = (by_reg.get(registration) if registration else None) or by_key.get(key)
        is_new = medicine is None
        if is_new:
            medicine = Medicine()
        before = None if is_new else [getattr(medicine, f) for f in UPDATE_FIELDS]
        medicine.brand_name = row["brand_name"]
        medicine.generic = generic
        medicine.strength = row["strength"]
        medicine.dosage_form = form
        medicine.manufacturer = maker
        medicine.is_sample = False  # it now comes from your file
        if row.get("brand_name_bn"):
            medicine.brand_name_bn = row["brand_name_bn"]
        if price is not None:
            medicine.price = price
        if row.get("price_unit"):
            medicine.price_unit = row["price_unit"]
        if updated_on:
            medicine.price_updated_on = updated_on
        if registration:
            medicine.dgda_registration_no = registration

        if is_new:
            base = slugify(f"{medicine.brand_name} {medicine.strength} {form.name}")[:240] or "medicine"
            slug, n = base, 2
            while slug in used_slugs:
                slug, n = f"{base}-{n}", n + 1
            used_slugs.add(slug)
            medicine.slug = slug
            medicine.prepare()
            to_create.append(medicine)
            result.created += 1
        else:
            medicine.prepare()
            # Re-importing a full list mostly changes nothing: writing only real changes keeps it fast.
            if [getattr(medicine, f) for f in UPDATE_FIELDS] == before:
                result.unchanged += 1
            else:
                result.updated += 1
                to_update[medicine.pk] = medicine

    if result.errors:
        return
    Medicine.objects.bulk_create(to_create, batch_size=BATCH_SIZE)
    Medicine.objects.bulk_update(
        to_update.values(), [f.removesuffix("_id") for f in UPDATE_FIELDS if f != "dgda_registration_no"] + ["dgda_registration_no"],
        batch_size=BATCH_SIZE,
    )


def import_generics(data, dry_run=False):
    result = ImportResult(dry_run=dry_run)
    rows, error = _read_rows(data, GENERIC_REQUIRED, GENERIC_COLUMNS)
    if error:
        result.errors.append(error)
        return result

    try:
        with transaction.atomic():
            generics, classes = {normalize(g.name): g for g in Generic.objects.all()}, _Lookup(DrugClass)
            seen = {}
            for line, row in rows:
                problems = (["generic is empty"] if not row.get("generic") else []) + _too_long(row)
                if problems:
                    result.errors.append(f"Line {line}: {'; '.join(problems)}")
                    continue
                key = normalize(row["generic"])
                if key in seen:
                    result.errors.append(f"Line {line}: same generic as line {seen[key]}")
                    continue
                seen[key] = line
                generic = generics.get(key)
                is_new = generic is None
                if is_new:
                    generic = Generic(name=row["generic"])
                if row.get("generic_bn"):
                    generic.name_bn = row["generic_bn"]
                for column in ("uses", "how_to_take", "side_effects", "warnings", "source"):
                    if row.get(column):
                        # Excel users can't easily type line breaks: "|" also starts a new point.
                        setattr(generic, column, row[column].replace("|", "\n"))
                if row.get("drug_class"):
                    generic.drug_class = classes.get(row["drug_class"], row.get("drug_class_bn", ""))
                generic.is_sample = False
                generic.save()
                if is_new:
                    result.created += 1
                else:
                    result.updated += 1
            if dry_run or result.errors:
                raise _Rollback
    except _Rollback:
        pass
    return result


IMPORTERS = {"medicines": import_medicines, "generics": import_generics}
