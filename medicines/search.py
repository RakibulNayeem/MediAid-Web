"""Medicine search.

Order of attempts, stopping at the first that finds something:
1. Every typed word starts a word in the medicine's search text (brand, generic, strength, form,
   in both languages), so "ace" finds Ace but not Par-ace-tamol. On PostgreSQL a trigram index
   makes this fast even with tens of thousands of rows.
2. Bangla typed, but the medicine only has an English name: try it spelled in English letters.
3. PostgreSQL only: closest spelling (trigram similarity), so "paracitamol" finds Paracetamol.
"""
from django.contrib.postgres.search import TrigramWordSimilarity
from django.db import connection
from django.db.models import Case, IntegerField, Q, Value, When

from .models import Generic, Medicine
from .text import bangla_to_latin, has_bangla, normalize

MAX_QUERY_LENGTH = 100
MIN_SIMILARITY = 0.3
MAX_FUZZY_RESULTS = 100


def _base():
    return Medicine.objects.filter(is_active=True).select_related("generic", "manufacturer", "dosage_form")


def _contains_all(queryset, query):
    for word in query.split():
        # search_text and the query are both lower-case already. "contains", not "icontains":
        # icontains wraps the column in UPPER(), which stops PostgreSQL using the trigram index.
        queryset = queryset.filter(search_text__contains=f" {word}")
    return queryset


def _ranked(queryset, query):
    """Brand name matches first, then the generic, then everything else."""
    first_word = query.split()[0]
    return queryset.annotate(
        rank=Case(
            When(Q(brand_name__iexact=first_word) | Q(brand_name_bn=first_word), then=Value(0)),
            When(Q(brand_name__istartswith=first_word) | Q(brand_name_bn__startswith=first_word), then=Value(1)),
            When(Q(generic__name__istartswith=first_word) | Q(generic__name_bn__startswith=first_word), then=Value(2)),
            default=Value(3),
            output_field=IntegerField(),
        )
    ).order_by("rank", "brand_name", "strength_key")


def _fuzzy(query):
    if connection.vendor != "postgresql":
        return Medicine.objects.none()
    return (
        _base()
        .annotate(similarity=TrigramWordSimilarity(query, "search_text"))
        .filter(similarity__gte=MIN_SIMILARITY)
        .order_by("-similarity", "brand_name", "strength_key")[:MAX_FUZZY_RESULTS]
    )


def search_medicines(raw_query):
    """Returns (queryset, was_fuzzy). was_fuzzy lets the page say 'closest matches'."""
    query = normalize(raw_query)[:MAX_QUERY_LENGTH]
    if not query:
        return Medicine.objects.none(), False

    matches = _contains_all(_base(), query)
    if matches.exists():
        return _ranked(matches, query), False

    latin = bangla_to_latin(query) if has_bangla(query) else ""
    if latin:
        matches = _contains_all(_base(), latin)
        if matches.exists():
            return _ranked(matches, latin), False

    return _fuzzy(latin or query), True


def matching_generics(raw_query):
    """Generics whose name matches, shown above the results as a shortcut to their info page."""
    query = normalize(raw_query)[:MAX_QUERY_LENGTH]
    if not query:
        return Generic.objects.none()
    filters = Q(name__icontains=query) | Q(name_bn__icontains=query)
    if has_bangla(query):
        filters |= Q(name__icontains=bangla_to_latin(query))
    return Generic.objects.filter(filters)[:3]
