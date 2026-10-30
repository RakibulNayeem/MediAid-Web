from decimal import Decimal

from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from .text import normalize, normalize_strength, sound_key


def unique_slug(model, text, pk=None):
    """A web-address-safe name that no other row uses. Falls back to 'item' for Bangla-only text."""
    base = slugify(text)[:180] or "item"
    slug, n = base, 2
    while model.objects.filter(slug=slug).exclude(pk=pk).exists():
        slug, n = f"{base}-{n}", n + 1
    return slug


class SluggedModel(models.Model):
    name = models.CharField(max_length=200, unique=True)
    name_bn = models.CharField(_("Bangla name"), max_length=200, blank=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    is_sample = models.BooleanField(_("sample data"), default=False, help_text=_("Test data, not from an official source."))

    class Meta:
        abstract = True
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(type(self), self.name, self.pk)
        super().save(*args, **kwargs)


def _refresh_search_text(medicines, **changed):
    """Names are part of a medicine's search text, so renaming a generic or form must update it."""
    for medicine in medicines:
        for name, value in changed.items():
            setattr(medicine, name, value)
        Medicine.objects.filter(pk=medicine.pk).update(
            search_text=medicine.build_search_text(), sound_text=medicine.build_sound_text(),
        )


class Manufacturer(SluggedModel):
    def get_absolute_url(self):
        return reverse("medicines:manufacturer_detail", args=[self.slug])


class DrugClass(SluggedModel):
    class Meta(SluggedModel.Meta):
        verbose_name_plural = "drug classes"

    def get_absolute_url(self):
        return reverse("medicines:drug_class_detail", args=[self.slug])


class DosageForm(SluggedModel):
    """Tablet, syrup, capsule... A table rather than free text, so 'Tablet' is always one thing."""

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        _refresh_search_text(self.medicines.select_related("generic"), dosage_form=self)


class Generic(SluggedModel):
    """The active ingredient. One information page, shared by all brands of this generic."""

    name = models.CharField(max_length=700, unique=True)  # combination vitamins have very long names
    drug_class = models.ForeignKey(DrugClass, null=True, blank=True, on_delete=models.SET_NULL, related_name="generics")
    uses = models.TextField(_("what it's for (Bangla)"), blank=True, help_text=_("One point per line."))
    how_to_take = models.TextField(_("how to take it (Bangla)"), blank=True, help_text=_("One point per line."))
    side_effects = models.TextField(_("common side effects (Bangla)"), blank=True, help_text=_("One point per line."))
    warnings = models.TextField(_("warnings (Bangla)"), blank=True, help_text=_("One point per line."))
    source = models.CharField(_("information source"), max_length=300, blank=True, help_text=_("e.g. the official leaflet this text came from."))

    def get_absolute_url(self):
        return reverse("medicines:generic_detail", args=[self.slug])

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        _refresh_search_text(self.medicines.select_related("dosage_form"), generic=self)


class Medicine(models.Model):
    """One brand at one strength in one form, e.g. Napa 500 mg Tablet."""

    brand_name = models.CharField(max_length=200)
    brand_name_bn = models.CharField(_("Bangla brand name"), max_length=200, blank=True)
    generic = models.ForeignKey(Generic, on_delete=models.PROTECT, related_name="medicines")
    strength = models.CharField(max_length=300, help_text=_("As printed, e.g. 500 mg"))
    dosage_form = models.ForeignKey(DosageForm, on_delete=models.PROTECT, related_name="medicines")
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.PROTECT, related_name="medicines")
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text=_("In taka, for the unit below."))
    price_unit = models.CharField(_("price is for"), max_length=50, blank=True, help_text=_("e.g. 1 tablet, 60 ml bottle. Savings are only shown between the same unit."))
    price_updated_on = models.DateField(null=True, blank=True)
    dgda_registration_no = models.CharField(_("DGDA registration no."), max_length=100, null=True, blank=True, unique=True)
    is_active = models.BooleanField(_("show on site"), default=True)
    is_popular = models.BooleanField(_("show on home page"), default=False)
    is_sample = models.BooleanField(_("sample data"), default=False, help_text=_("Test data, not from an official source."))
    view_count = models.PositiveIntegerField(default=0, editable=False)

    slug = models.SlugField(max_length=255, unique=True, blank=True)
    # Filled in automatically. They make comparing and searching fast.
    strength_key = models.CharField(max_length=300, editable=False, db_index=True)
    search_text = models.TextField(editable=False, blank=True)
    sound_text = models.TextField(editable=False, blank=True)

    class Meta:
        ordering = ["brand_name", "strength_key"]
        indexes = [
            models.Index(fields=["generic", "strength_key", "dosage_form", "price"], name="medicine_alternatives_idx"),
            models.Index(fields=["-view_count"], name="medicine_views_idx"),
        ]
        # The trigram index on search_text is added in a PostgreSQL-only migration.

    def __str__(self):
        return f"{self.brand_name} {self.strength} {self.dosage_form}"

    def get_absolute_url(self):
        return reverse("medicines:medicine_detail", args=[self.slug])

    def build_search_text(self):
        parts = [
            self.brand_name, self.brand_name_bn, self.generic.name, self.generic.name_bn,
            self.strength_key, self.dosage_form.name, self.dosage_form.name_bn,
        ]
        # The leading space lets the search match the start of any word (see search.py).
        return " " + normalize(" ".join(p for p in parts if p))

    def build_sound_text(self):
        """How the brand and generic names sound, for catching other spellings (see text.sound_key)."""
        words = f"{self.brand_name} {self.generic.name}".split()
        return " " + " ".join(key for key in map(sound_key, words) if key) + " "

    def prepare(self):
        """Fill in the automatic fields. The bulk CSV import calls this directly."""
        self.strength_key = normalize_strength(self.strength)
        self.search_text = self.build_search_text()
        self.sound_text = self.build_sound_text()
        if not self.slug:
            self.slug = unique_slug(Medicine, f"{self.brand_name} {self.strength} {self.dosage_form.name}", self.pk)

    def save(self, *args, **kwargs):
        self.prepare()
        super().save(*args, **kwargs)

    def alternatives(self):
        """Every active brand with the same generic + strength + dosage form, cheapest first (this one included)."""
        return (
            Medicine.objects.filter(
                generic_id=self.generic_id, strength_key=self.strength_key, dosage_form_id=self.dosage_form_id, is_active=True,
            )
            .select_related("manufacturer", "generic", "dosage_form")
            .order_by(models.F("price").asc(nulls_last=True), "brand_name")
        )

    def saving_against(self, other):
        """How much cheaper `other` is, or None if they can't be fairly compared."""
        if self.price is None or other.price is None:
            return None
        # A 60 ml bottle and a 100 ml bottle aren't comparable, and an unknown unit could be either.
        if not self.price_unit or self.price_unit.lower() != other.price_unit.lower():
            return None
        return self.price - other.price if other.price < self.price else None


def saving_percent(price, saving):
    if not price:
        return 0
    return int((Decimal(saving) / Decimal(price) * 100).to_integral_value())
