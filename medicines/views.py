from django.core.paginator import Paginator
from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404, render

from .models import DrugClass, Generic, Manufacturer, Medicine, saving_percent
from .search import matching_generics, search_medicines

PAGE_SIZE = 20
_ACTIVE_COUNT = Count("medicines", filter=Q(medicines__is_active=True))


def _page(request, items):
    return Paginator(items, PAGE_SIZE).get_page(request.GET.get("page"))


def search(request):
    query = request.GET.get("q", "").strip()
    results, was_fuzzy = search_medicines(query)
    return render(request, "medicines/search.html", {
        "query": query,
        "page": _page(request, results),
        "was_fuzzy": was_fuzzy,
        "generics": matching_generics(query),
    })


def medicine_detail(request, slug):
    medicine = get_object_or_404(
        Medicine.objects.select_related("generic__drug_class", "manufacturer", "dosage_form"), slug=slug, is_active=True,
    )
    # Powers "commonly searched" on the home page. F() avoids losing counts when two people open it at once.
    Medicine.objects.filter(pk=medicine.pk).update(view_count=F("view_count") + 1)

    alternatives = []
    best_saving = None
    for other in medicine.alternatives():
        saving = medicine.saving_against(other)
        alternatives.append({
            "medicine": other,
            "is_current": other.pk == medicine.pk,
            "saving": saving,
            "percent": saving_percent(medicine.price, saving) if saving else 0,
        })
        if saving and (best_saving is None or saving > best_saving):
            best_saving = saving
    return render(request, "medicines/medicine_detail.html", {
        "medicine": medicine,
        "alternatives": alternatives,
        "best_saving": best_saving,
    })


def generic_list(request):
    query = request.GET.get("q", "").strip()
    generics = Generic.objects.annotate(brand_count=_ACTIVE_COUNT).select_related("drug_class").order_by("name")
    if query:
        generics = generics.filter(Q(name__icontains=query) | Q(name_bn__icontains=query))
    return render(request, "medicines/generic_list.html", {"page": _page(request, generics), "query": query})


def generic_detail(request, slug):
    generic = get_object_or_404(Generic.objects.select_related("drug_class"), slug=slug)
    medicines = (
        generic.medicines.filter(is_active=True)
        .select_related("generic", "manufacturer", "dosage_form")
        .order_by("strength_key", F("price").asc(nulls_last=True))
    )
    return render(request, "medicines/generic_detail.html", {"generic": generic, "page": _page(request, medicines)})


def manufacturer_list(request):
    manufacturers = Manufacturer.objects.annotate(brand_count=_ACTIVE_COUNT).filter(brand_count__gt=0).order_by("name")
    return render(request, "medicines/browse_list.html", {"page": _page(request, manufacturers), "kind": "manufacturer"})


def manufacturer_detail(request, slug):
    manufacturer = get_object_or_404(Manufacturer, slug=slug)
    medicines = manufacturer.medicines.filter(is_active=True).select_related("generic", "manufacturer", "dosage_form")
    return render(request, "medicines/browse_detail.html", {"item": manufacturer, "page": _page(request, medicines), "kind": "manufacturer"})


def drug_class_list(request):
    classes = DrugClass.objects.annotate(brand_count=Count("generics", distinct=True)).order_by("name")
    return render(request, "medicines/browse_list.html", {"page": _page(request, classes), "kind": "class"})


def drug_class_detail(request, slug):
    drug_class = get_object_or_404(DrugClass, slug=slug)
    generics = drug_class.generics.annotate(brand_count=_ACTIVE_COUNT).order_by("name")
    return render(request, "medicines/drug_class_detail.html", {"item": drug_class, "page": _page(request, generics)})
