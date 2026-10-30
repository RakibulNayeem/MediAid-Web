from django.db.models import F, Q
from django.shortcuts import render

from medicines.models import Medicine, saving_percent

SAVE_MONEY_COUNT = 6
COMMON_COUNT = 8


def _save_money_cards():
    """Popular medicines that have a cheaper brand, biggest percentage saving first."""
    popular = list(Medicine.objects.filter(is_active=True, is_popular=True).select_related("generic", "dosage_form", "manufacturer"))
    siblings = {}
    for medicine in Medicine.objects.filter(
        is_active=True, generic_id__in={m.generic_id for m in popular}, price__isnull=False,
    ).select_related("manufacturer"):
        siblings.setdefault((medicine.generic_id, medicine.strength_key, medicine.dosage_form_id), []).append(medicine)

    cards = []
    for medicine in popular:
        options = siblings.get((medicine.generic_id, medicine.strength_key, medicine.dosage_form_id), [])
        savings = [(medicine.saving_against(other), other) for other in options]
        savings = [pair for pair in savings if pair[0]]
        if savings:
            saving, cheapest = max(savings, key=lambda pair: pair[0])
            cards.append({
                "medicine": medicine,
                "cheapest": cheapest,
                "saving": saving,
                "percent": saving_percent(medicine.price, saving),
            })
    cards.sort(key=lambda card: card["percent"], reverse=True)
    return cards[:SAVE_MONEY_COUNT]


def home(request):
    common = (
        # Only medicines people really opened or you picked, not the first names in the alphabet.
        Medicine.objects.filter(Q(view_count__gt=0) | Q(search_count__gt=0) | Q(is_popular=True), is_active=True)
        .select_related("generic", "dosage_form")
        .order_by((F("view_count") + F("search_count")).desc(), F("is_popular").desc(), "brand_name")[:COMMON_COUNT]
    )
    real_medicines = Medicine.objects.filter(is_active=True, is_sample=False)
    return render(request, "core/home.html", {
        "save_money": _save_money_cards(),
        "common": common,
        "medicine_count": f"{count:,}" if (count := real_medicines.count()) else "",
        "maker_count": real_medicines.values("manufacturer").distinct().count(),
    })
