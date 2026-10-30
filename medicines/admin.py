from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.urls import path

from .forms import CsvImportForm
from .importer import GENERIC_COLUMNS, IMPORTERS, MAX_ERRORS_SHOWN, MEDICINE_COLUMNS
from .models import DosageForm, DrugClass, Generic, Manufacturer, Medicine


@admin.register(Manufacturer, DrugClass, DosageForm)
class NamedAdmin(admin.ModelAdmin):
    list_display = ["name", "name_bn", "name_bn_auto", "is_sample"]
    list_filter = ["is_sample", "name_bn_auto"]
    search_fields = ["name", "name_bn"]
    prepopulated_fields = {"slug": ["name"]}

    def save_model(self, request, obj, form, change):
        if "name_bn" in form.changed_data:  # a person has checked it now
            obj.name_bn_auto = False
        super().save_model(request, obj, form, change)


@admin.register(Generic)
class GenericAdmin(NamedAdmin):
    list_display = ["name", "name_bn", "drug_class", "has_info", "is_sample"]
    list_filter = ["is_sample", "name_bn_auto", "drug_class"]
    autocomplete_fields = ["drug_class"]

    @admin.display(boolean=True, description="info page filled in")
    def has_info(self, obj):
        return bool(obj.uses)


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ["brand_name", "strength", "dosage_form", "generic", "manufacturer", "price", "price_unit", "is_active", "is_popular", "is_sample"]
    list_filter = ["is_sample", "is_active", "is_popular", "brand_name_bn_auto", "dosage_form"]
    list_editable = ["price", "is_active", "is_popular"]
    search_fields = ["brand_name", "brand_name_bn", "generic__name", "generic__name_bn", "dgda_registration_no"]
    autocomplete_fields = ["generic", "dosage_form", "manufacturer"]
    prepopulated_fields = {"slug": ["brand_name", "strength"]}
    list_select_related = ["generic", "dosage_form", "manufacturer"]
    change_list_template = "admin/medicines/medicine/change_list.html"

    def save_model(self, request, obj, form, change):
        if "brand_name_bn" in form.changed_data:
            obj.brand_name_bn_auto = False
        super().save_model(request, obj, form, change)

    def get_urls(self):
        return [
            path("import-csv/", self.admin_site.admin_view(self.import_csv), name="medicines_import_csv"),
        ] + super().get_urls()

    def import_csv(self, request):
        if not self.has_add_permission(request):
            raise PermissionDenied
        form = CsvImportForm(request.POST or None, request.FILES or None)
        result = None
        if request.method == "POST" and form.is_valid():
            result = IMPORTERS[form.cleaned_data["kind"]](form.cleaned_data["file"].read(), dry_run=form.cleaned_data["dry_run"])
            if result.ok and not result.dry_run:
                messages.success(request, f"Saved: {result.created} new, {result.updated} updated, {result.unchanged} unchanged.")
        return render(request, "admin/medicines/medicine/import_csv.html", {
            **self.admin_site.each_context(request),
            "title": "Import CSV",
            "opts": self.model._meta,
            "form": form,
            "result": result,
            "errors_shown": result.errors[:MAX_ERRORS_SHOWN] if result else [],
            "errors_hidden": max(len(result.errors) - MAX_ERRORS_SHOWN, 0) if result else 0,
            "medicine_columns": MEDICINE_COLUMNS,
            "generic_columns": GENERIC_COLUMNS,
        })
