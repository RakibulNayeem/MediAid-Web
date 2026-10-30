"""Writes English medicine names in Bangla letters, by sound.

Companies choose their own Bangla spellings, so this will sometimes differ from the packet.
Names made here are marked as automatic so people can review them, and English stays visible.
"""
import re

HASANTA = "্"
# Longest spellings first.
CONSONANTS = [
    ("sch", "স্ক"), ("tch", "চ"), ("ph", "ফ"), ("th", "থ"), ("ch", "চ"), ("sh", "শ"), ("kh", "খ"), ("gh", "ঘ"),
    ("dh", "ধ"), ("bh", "ভ"), ("ck", "ক"), ("qu", "কু"), ("b", "ব"), ("d", "ড"), ("f", "ফ"), ("h", "হ"),
    ("j", "জ"), ("k", "ক"), ("l", "ল"), ("m", "ম"), ("n", "ন"), ("p", "প"), ("q", "ক"), ("r", "র"), ("s", "স"),
    ("t", "ট"), ("v", "ভ"), ("w", "ও"), ("x", "ক্স"), ("z", "জ"),
]
# (spelling, at the start of a word, after a consonant)
VOWELS = [
    ("ee", "ই", "ী"), ("ea", "ই", "ী"), ("oo", "উ", "ু"), ("ai", "আই", "াই"), ("ay", "এ", "ে"), ("au", "অ", "ো"),
    ("ou", "আউ", "াউ"), ("ia", "ইয়া", "িয়া"), ("io", "ইও", "িও"), ("a", "আ", "া"), ("e", "এ", "ে"), ("i", "ই", "ি"),
    ("o", "ও", "ো"), ("u", "উ", "ু"), ("y", "ই", "ি"),
]
# Well-known names, spelled the way people write them.
KNOWN_WORDS = {
    "paracetamol": "প্যারাসিটামল", "omeprazole": "ওমিপ্রাজল", "esomeprazole": "ইসোমিপ্রাজল", "pantoprazole": "প্যান্টোপ্রাজল",
    "cetirizine": "সেটিরিজিন", "fexofenadine": "ফেক্সোফেনাডিন", "montelukast": "মন্টিলুকাস্ট", "azithromycin": "অ্যাজিথ্রোমাইসিন",
    "amoxicillin": "অ্যামোক্সিসিলিন", "cefixime": "সেফিক্সিম", "ciprofloxacin": "সিপ্রোফ্লক্সাসিন", "metronidazole": "মেট্রোনিডাজল",
    "amlodipine": "অ্যামলোডিপিন", "losartan": "লোসারটান", "metformin": "মেটফরমিন", "atorvastatin": "অ্যাটোরভাস্টাটিন",
    "salbutamol": "সালবিউটামল", "domperidone": "ডমপেরিডন", "ibuprofen": "আইবুপ্রোফেন", "aspirin": "অ্যাসপিরিন",
    "potassium": "পটাশিয়াম", "sodium": "সোডিয়াম", "calcium": "ক্যালসিয়াম", "hydrochloride": "হাইড্রোক্লোরাইড", "vitamin": "ভিটামিন",
    "acid": "অ্যাসিড", "zinc": "জিংক", "iron": "আয়রন", "and": "ও",
    "napa": "নাপা", "ace": "এইস", "seclo": "সেকলো", "maxpro": "ম্যাক্সপ্রো", "fexo": "ফেক্সো", "monas": "মোনাস", "zimax": "জিম্যাক্স",
    "camlodin": "ক্যামলোডিন", "comet": "কমেট", "alatrol": "এলাট্রল",
}
FORM_WORDS = {
    "tablet": "ট্যাবলেট", "capsule": "ক্যাপসুল", "syrup": "সিরাপ", "injection": "ইনজেকশন", "suspension": "সাসপেনশন",
    "powder": "পাউডার", "for": "", "eye": "চোখের", "ear": "কানের", "nasal": "নাকের", "drops": "ড্রপ", "drop": "ড্রপ", "cream": "ক্রিম",
    "ointment": "মলম", "solution": "দ্রবণ", "oral": "মুখে খাওয়ার", "gel": "জেল", "suppository": "সাপোজিটরি", "inhalation": "ইনহেলেশন",
    "aerosol": "অ্যারোসল", "spray": "স্প্রে", "lotion": "লোশন", "sachet": "স্যাশে", "infusion": "ইনফিউশন", "paediatric": "শিশুদের",
    "saline": "স্যালাইন", "topical": "ত্বকে লাগানোর", "mouth": "মুখের", "wash": "ওয়াশ", "emulsion": "ইমালশন", "chewable": "চিবিয়ে খাওয়ার", "xr": "XR", "er": "ER", "sr": "SR", "cr": "CR", "dr": "DR", "odt": "ODT", "mups": "MUPS",
    "inhaler": "ইনহেলার", "vaccine": "টিকা", "syringe": "সিরিঞ্জ", "nebuliser": "নেবুলাইজার", "dry": "ড্রাই", "dialysis": "ডায়ালাইসিস",
    "orodispersible": "মুখে গলে যাওয়া", "vaginal": "যোনিপথের", "scalp": "মাথার ত্বকের",
    "soft": "সফট", "gelatin": "জেলাটিন", "dispersible": "পানিতে গোলানো", "and": "ও", "hand": "হাতের", "rub": "রাব", "shampoo": "শ্যাম্পু",
    "soap": "সাবান", "liquid": "তরল", "granules": "দানাদার", "vial": "ভায়াল", "ampoule": "অ্যাম্পুল",
}
_WORD = re.compile(r"[A-Za-z]+|[^A-Za-z]+")


def _joins(first, second):
    """Only join letters where Bangla readers expect it (প্র, ক্ল, স্ট). Other joins are hard to read."""
    if second in ("র", "ল") and first not in ("র", "ল"):
        return True
    return first == "স" and second in ("ক", "ট", "প", "ম", "ন")


def _word(word):
    known = KNOWN_WORDS.get(word.lower())
    if known:
        return known
    # Short capitals with no vowels are initials, like HCL: leave them as they are.
    if word.isupper() and (len(word) <= 4 or not re.search(r"[AEIOU]", word)):
        return word
    text = re.sub(r"(.)\1+", r"\1", word.lower())
    text = re.sub(r"(?<=[a-z]{2})e$", "", text)  # the silent e of "amlodipine"
    out, i, after_consonant = [], 0, False
    while i < len(text):
        rest = text[i:]
        if rest[0] == "c":
            letters, bangla = "c", "স" if rest[1:2] in ("e", "i", "y") else "ক"
            if rest.startswith("ch"):
                letters, bangla = "ch", "চ"
            elif rest.startswith("ck"):
                letters, bangla = "ck", "ক"
        elif rest[0] == "g":
            letters, bangla = "g", "জ" if rest[1:2] in ("e", "i", "y") else "গ"
            if rest.startswith("gh"):
                letters, bangla = "gh", "ঘ"
        elif rest[0] == "y" and not out:
            letters, bangla = "y", "ই"
            out.append(bangla)
            i += 1
            continue
        else:
            match = next(((l, b) for l, b in CONSONANTS if rest.startswith(l)), None)
            if match is None:
                vowel = next((v for v in VOWELS if rest.startswith(v[0])), None)
                if vowel is None:
                    out.append(rest[0])
                    after_consonant = False
                    i += 1
                    continue
                out.append(vowel[2] if after_consonant else vowel[1])
                after_consonant = False
                i += len(vowel[0])
                continue
            letters, bangla = match
        if after_consonant and _joins(out[-1], bangla):
            out.append(HASANTA)
        out.append(bangla)
        after_consonant = True
        i += len(letters)
    return "".join(out)


def to_bangla(name):
    """'Seclo 20' -> 'সেকলো 20'. Numbers and symbols stay as they are."""
    return "".join(_word(part) if part[0].isalpha() else part for part in _WORD.findall(name))


def form_to_bangla(name):
    """Medicine forms are translated word by word: 'Eye Drops' -> 'চোখের ড্রপ'."""
    words = [FORM_WORDS.get(word.lower(), to_bangla(word)) for word in name.split()]
    return " ".join(word for word in words if word)
