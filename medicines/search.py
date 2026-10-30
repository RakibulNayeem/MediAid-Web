"""Medicine search.

Order of attempts, stopping at the first that finds something:
1. Every typed word starts a word in the medicine's search text (brand, generic, strength, form,
   in both languages), so "ace" finds Ace but not Par-ace-tamol. On PostgreSQL a trigram index
   makes this fast even with tens of thousands of rows.
2. Bangla typed, but the medicine only has an English name: try it spelled in English letters.
3. Same sound, different spelling: "paracitamol" and "প্যারাসিটামল" both find Paracetamol.
4. PostgreSQL only: closest spelling (trigram similarity). These can be different medicines,
   so the page labels them as closest matches, not as what was asked for.
"""
from django.contrib.postgres.search import TrigramWordSimilarity
from django.db import connection
from django.db.models import Case, IntegerField, Q, Value, When
from django.db.models.functions import Length

from .models import Generic, Medicine
from .text import bangla_to_latin, has_bangla, normalize, sound_key

MAX_QUERY_LENGTH = 100
MIN_SIMILARITY = 0.4
MIN_SOUND_LENGTH = 3  # shorter sound keys would match far too many medicines
MIN_SOUND_PREFIX_LENGTH = 5  # "skl" alone must not find Cyclophosphamide when looking for Seclo
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


def _same_sound(query):
    keys = [sound_key(word) for word in query.split()]
    keys = [key for key in keys if len(key) >= MIN_SOUND_LENGTH]
    if not keys:
        return Medicine.objects.none()
    whole_words = _base()
    for key in keys:
        whole_words = whole_words.filter(sound_text__contains=f" {key} ")
    if whole_words.exists() or min(map(len, keys)) < MIN_SOUND_PREFIX_LENGTH:
        return whole_words
    word_starts = _base()
    for key in keys:
        word_starts = word_starts.filter(sound_text__contains=f" {key}")
    return word_starts


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

    matches = _same_sound(query)
    if matches.exists():
        # Brand matches first: the sound key of the brand starts the sound text.
        first_key = sound_key(query.split()[0])
        return matches.annotate(
            rank=Case(When(sound_text__startswith=f" {first_key}", then=Value(0)), default=Value(1), output_field=IntegerField())
        ).order_by("rank", "brand_name", "strength_key"), False

    return _fuzzy(latin or query), True


def matching_generics(raw_query):
    """Generics whose name matches, shown above the results as a shortcut to their info page."""
    query = normalize(raw_query)[:MAX_QUERY_LENGTH]
    if not query:
        return Generic.objects.none()
    filters = Q(name__icontains=query) | Q(name_bn__icontains=query)
    if has_bangla(query):
        filters |= Q(name__icontains=bangla_to_latin(query))
    shortest_first = Length("name").asc()  # plain Paracetamol before Caffeine + Paracetamol
    generics = Generic.objects.filter(filters).order_by(shortest_first)[:3]
    if generics:
        return generics
    # Nothing by spelling: use the generics of medicines that sound the same.
    return Generic.objects.filter(pk__in=_same_sound(query).values("generic_id")).order_by(shortest_first)[:3]
