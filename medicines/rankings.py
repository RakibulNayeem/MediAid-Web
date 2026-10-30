"""Leaderboards. Only totals are stored, never who searched."""
from django.db.models import Max, Q, Sum
from django.db.models.functions import Lower

from .models import Medicine


def most_searched(limit):
    # All strengths and forms of a brand count together, so Napa appears once.
    return (
        Medicine.objects.filter(Q(search_count__gt=0) | Q(view_count__gt=0), is_active=True)
        .annotate(key=Lower("brand_name"))
        .values("key")
        .annotate(total=Sum("search_count") + Sum("view_count"), brand=Max("brand_name"), brand_bn=Max("brand_name_bn"))
        .order_by("-total", "key")[:limit]
    )
