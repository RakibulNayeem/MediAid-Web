from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _

from core.templatetags.mediaid import dual, localized, num

from .models import DrugClass, Generic, Manufacturer, Medicine, saving_percent
from .search import matching_generics, search_medicines

MAX_SUGGESTIONS = 8
MAX_GENERIC_SUGGESTIONS = 2

PAGE_SIZE = 20
MAX_ALTERNATIVES = 30  # common generics have over 100 brands
_ACTIVE_COUNT = Count("medicines", filter=Q(medicines__is_active=True))


def _page(request, items):
    return Paginator(items, PAGE_SIZE).get_page(request.GET.get("page"))


def search(request):
    query = request.GET.get("q", "").strip()
    results, was_fuzzy = search_medicines(query)
    return render(request, "medicines/search.html", {
        "query": query,
        "autofocus": not query,  # arriving from the header's search icon: ready to type
        "page": _page(request, results),
        "was_fuzzy": was_fuzzy,
        "generics": matching_generics(query),
    })


def _add_price_bars(alternatives, medicine):
    """Marks the cheapest brand and sizes each price bar. Only brands priced in the same unit are compared."""
    comparable = [
        row for row in alternatives
        if medicine.price_unit and row["medicine"].price and row["medicine"].price_unit.lower() == medicine.price_unit.lower()
    ]
    if len(comparable) < 2:
        return
    highest = max(row["medicine"].price for row in comparable)
    lowest = min(row["medicine"].price for row in comparable)
    for row in comparable:
        row["bar"] = int(row["medicine"].price / highest * 100)
        row["is_cheapest"] = row["medicine"].price == lowest and lowest < highest


def suggest(request):
    """Suggestions under the search box. Only sure matches: a lookalike name here could mislead."""
    query = request.GET.get("q", "").strip()
    results = []
    if len(query) >= 2:
        results += [
            {"title": dual(generic), "detail": _("Generic"), "url": generic.get_absolute_url()}
            for generic in matching_generics(query)[:MAX_GENERIC_SUGGESTIONS]
        ]
        medicines, _was_fuzzy = search_medicines(query, allow_closest=False)
        results += [
            {
                "title": f"{dual(medicine, 'brand_name')} {num(medicine.strength)}",
                "detail": f"{localized(medicine.dosage_form)} · {dual(medicine.generic)} · {localized(medicine.manufacturer)}",
                "url": medicine.get_absolute_url(),
            }
            for medicine in medicines[:MAX_SUGGESTIONS - len(results)]
        ]
    return JsonResponse({"results": results})


def medicine_detail(request, slug):
    medicine = get_object_or_404(
        Medicine.objects.select_related("generic__drug_class", "manufacturer", "dosage_form"), slug=slug, is_active=True,
    )
    # Powers "commonly searched" on the home page. F() avoids losing counts when two people open it at once.
    Medicine.objects.filter(pk=medicine.pk).update(view_count=F("view_count") + 1)

    alternatives = []
    best_saving = None
    all_alternatives = medicine.alternatives()
    for other in all_alternatives[:MAX_ALTERNATIVES]:
        saving = medicine.saving_against(other)
        alternatives.append({
            "medicine": other,
            "is_current": other.pk == medicine.pk,
            "saving": saving,
            "percent": saving_percent(medicine.price, saving) if saving else 0,
        })
        if saving and (best_saving is None or saving > best_saving):
            best_saving = saving
    _add_price_bars(alternatives, medicine)
    return render(request, "medicines/medicine_detail.html", {
        "medicine": medicine,
        "alternatives": alternatives,
        "best_saving": best_saving,
        "more_alternatives": max(all_alternatives.count() - MAX_ALTERNATIVES, 0),
        "any_price_missing": any(row["medicine"].price is None for row in alternatives),
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
