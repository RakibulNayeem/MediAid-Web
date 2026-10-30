"""Text clean-up shared by the search and the CSV import."""
import re
import unicodedata

_BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

# Bangla letters -> rough English sound. It doesn't need to be exact: the fuzzy search
# only needs "সেকলো" to look enough like "seclo" to find it.
_VOWELS = {"অ": "o", "আ": "a", "ই": "i", "ঈ": "i", "উ": "u", "ঊ": "u", "ঋ": "ri", "এ": "e", "ঐ": "oi", "ও": "o", "ঔ": "ou"}
_SIGNS = {"া": "a", "ি": "i", "ী": "i", "ু": "u", "ূ": "u", "ৃ": "ri", "ে": "e", "ৈ": "oi", "ো": "o", "ৌ": "ou"}
_CONSONANTS = {
    "ক": "k", "খ": "kh", "গ": "g", "ঘ": "gh", "ঙ": "ng", "চ": "c", "ছ": "ch", "জ": "j", "ঝ": "jh", "ঞ": "n",
    "ট": "t", "ঠ": "th", "ড": "d", "ঢ": "dh", "ণ": "n", "ত": "t", "থ": "th", "দ": "d", "ধ": "dh", "ন": "n",
    "প": "p", "ফ": "f", "ব": "b", "ভ": "v", "ম": "m", "য": "j", "র": "r", "ল": "l", "শ": "s", "ষ": "s",
    "স": "s", "হ": "h", "ৎ": "t", "ং": "ng", "ঃ": "", "ঁ": "",
    "\u09a1\u09bc": "r", "\u09a2\u09bc": "r", "\u09af\u09bc": "y",  # ড়, ঢ়, য় (letter + dot)
}
_HASANTA = "\u09cd"
_NUKTA = "\u09bc"


def normalize(text):
    """Lower-case, Bangla digits -> English digits, one consistent Unicode form, single spaces."""
    text = unicodedata.normalize("NFC", text or "").translate(_BN_DIGITS).lower()
    return " ".join(text.split())


def normalize_strength(text):
    """'500 MG' and '500mg' must count as the same strength when comparing brands."""
    return re.sub(r"\s+", "", normalize(text))


def has_bangla(text):
    return any("ঀ" <= ch <= "৿" for ch in text)


def bangla_to_latin(text):
    """Rough romanisation, because official drug lists only have English names."""
    text = unicodedata.normalize("NFC", text)  # NFC always stores ড় as ড + dot
    out = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in _CONSONANTS:
            if text[i + 1:i + 2] == _NUKTA:
                ch += _NUKTA
                i += 1
            out.append(_CONSONANTS[ch])
        elif ch == _HASANTA:
            if text[i + 1:i + 2] == "য":  # প্যা sounds like "pa": skip the joined য
                i += 1
        elif ch in _SIGNS:
            out.append(_SIGNS[ch])
        elif ch in _VOWELS:
            out.append(_VOWELS[ch])
        else:
            out.append(ch)
        i += 1
    return "".join(out)


_SOUND_SWAPS = [("ph", "f"), ("ck", "k"), ("x", "ks"), ("q", "k"), ("v", "b"), ("z", "j"), ("w", "")]
_SOFT_C = re.compile(r"c(?=[eiy])")


def sound_key(word):
    """A word's consonants, so different spellings of one sound match.

    paracetamol, paracitamol and প্যারাসিটামল all become "prstml"; seclo and সেকলো become "skl".
    """
    word = bangla_to_latin(normalize(word))
    word = _SOFT_C.sub("s", word).replace("c", "k")
    for old, new in _SOUND_SWAPS:
        word = word.replace(old, new)
    word = re.sub(r"([bdgkt])h", r"\1", word)  # Bangla often spells t, d... with an extra h sound
    word = re.sub(r"[^a-z0-9]", "", word)
    word = re.sub(r"^[aeiouy]+", "a", word)  # a word's opening vowel sound is spelled many ways: o, a, অ্যা
    word = word[:1] + re.sub(r"[aeiouy]", "", word[1:])
    return re.sub(r"(.)\1+", r"\1", word)  # "ll" counts as "l"
