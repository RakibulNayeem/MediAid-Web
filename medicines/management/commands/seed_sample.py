"""Load a small set of SAMPLE data for testing. Every row is marked is_sample=True.

The prices are invented. The brand-to-company pairs and health text were written from general
knowledge and were not checked against DGDA lists or leaflets. Real data comes from the CSV import.

    python manage.py seed_sample          add the sample data
    python manage.py seed_sample --clear  remove it again (rows you imported are not touched)
"""
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from medicines.models import DosageForm, DrugClass, Generic, Manufacturer, Medicine

MANUFACTURERS = {
    "Square": ("Square Pharmaceuticals", "স্কয়ার ফার্মাসিউটিক্যালস"),
    "Beximco": ("Beximco Pharmaceuticals", "বেক্সিমকো ফার্মাসিউটিক্যালস"),
    "Incepta": ("Incepta Pharmaceuticals", "ইনসেপ্টা ফার্মাসিউটিক্যালস"),
    "Renata": ("Renata", "রেনাটা"),
    "Eskayef": ("Eskayef Pharmaceuticals", "এসকেএফ ফার্মাসিউটিক্যালস"),
    "ACME": ("The ACME Laboratories", "দি একমি ল্যাবরেটরিজ"),
    "Opsonin": ("Opsonin Pharma", "অপসোনিন ফার্মা"),
    "Healthcare": ("Healthcare Pharmaceuticals", "হেলথকেয়ার ফার্মাসিউটিক্যালস"),
    "ACI": ("ACI Limited", "এসিআই লিমিটেড"),
}

FORMS = {
    "Tablet": "ট্যাবলেট",
    "Capsule": "ক্যাপসুল",
    "Syrup": "সিরাপ",
}

COMMON_HOW = "ডাক্তারের পরামর্শ বা প্যাকেটের নির্দেশনা অনুযায়ী খান।"

# name, Bangla name, class, Bangla class, uses, how to take, side effects, warnings,
# [(brand, Bangla brand, maker, strength, form, price, unit, popular)]
GENERICS = [
    ("Paracetamol", "প্যারাসিটামল", "Pain relief and fever", "ব্যথা ও জ্বর উপশম",
     "জ্বর কমাতে\nমাথাব্যথা, দাঁতব্যথা ও শরীরব্যথায়",
     f"{COMMON_HOW}\nখালি পেটেও খাওয়া যায়।",
     "সাধারণত পার্শ্বপ্রতিক্রিয়া কম\nকখনো চামড়ায় র‍্যাশ হতে পারে",
     "নির্ধারিত মাত্রার বেশি খেলে লিভারের মারাত্মক ক্ষতি হতে পারে।\nঅন্য কোনো ওষুধে প্যারাসিটামল আছে কি না দেখে নিন।\nলিভারের রোগ থাকলে আগে ডাক্তারকে জানান।",
     [("Napa", "নাপা", "Beximco", "500 mg", "Tablet", "1.20", "1 tablet", True),
      ("Ace", "এইস", "Square", "500 mg", "Tablet", "1.10", "1 tablet", False),
      ("Xpa", "এক্সপা", "Incepta", "500 mg", "Tablet", "0.90", "1 tablet", False)]),
    ("Omeprazole", "ওমিপ্রাজল", "Acid reducer (PPI)", "এসিড কমানোর ওষুধ",
     "গ্যাস্ট্রিক ও বুক জ্বালায়\nপাকস্থলীর ক্ষতে",
     f"{COMMON_HOW}\nসাধারণত খাবারের আগে খেতে হয়।",
     "মাথাব্যথা\nপেটব্যথা, ডায়রিয়া বা বমি ভাব",
     "দীর্ঘদিন খাওয়ার আগে ডাক্তারের পরামর্শ নিন।\nকালো পায়খানা বা রক্তবমি হলে দ্রুত ডাক্তার দেখান।",
     [("Seclo", "সেকলো", "Square", "20 mg", "Capsule", "6.00", "1 capsule", True),
      ("Losectil", "লোসেকটিল", "Eskayef", "20 mg", "Capsule", "5.00", "1 capsule", False)]),
    ("Esomeprazole", "ইসোমিপ্রাজল", "Acid reducer (PPI)", "এসিড কমানোর ওষুধ",
     "গ্যাস্ট্রিক ও বুক জ্বালায়\nএসিড রিফ্লাক্সে",
     f"{COMMON_HOW}\nসাধারণত খাবারের আগে খেতে হয়।",
     "মাথাব্যথা\nপেটব্যথা, ডায়রিয়া বা বমি ভাব",
     "দীর্ঘদিন খাওয়ার আগে ডাক্তারের পরামর্শ নিন।\nকালো পায়খানা বা রক্তবমি হলে দ্রুত ডাক্তার দেখান।",
     [("Maxpro", "ম্যাক্সপ্রো", "Renata", "20 mg", "Tablet", "7.00", "1 tablet", True),
      ("Sergel", "সার্জেল", "Healthcare", "20 mg", "Tablet", "7.50", "1 tablet", False),
      ("Esonix", "ইসোনিক্স", "Incepta", "20 mg", "Tablet", "6.00", "1 tablet", False)]),
    ("Pantoprazole", "প্যান্টোপ্রাজল", "Acid reducer (PPI)", "এসিড কমানোর ওষুধ",
     "গ্যাস্ট্রিক ও বুক জ্বালায়\nপাকস্থলীর ক্ষতে",
     f"{COMMON_HOW}\nসাধারণত খাবারের আগে খেতে হয়।",
     "মাথাব্যথা\nডায়রিয়া",
     "দীর্ঘদিন খাওয়ার আগে ডাক্তারের পরামর্শ নিন।",
     [("Pantonix", "প্যান্টোনিক্স", "Incepta", "20 mg", "Tablet", "5.00", "1 tablet", False),
      ("Trupan", "ট্রুপ্যান", "Square", "20 mg", "Tablet", "5.50", "1 tablet", False)]),
    ("Cetirizine", "সেটিরিজিন", "Antihistamine", "অ্যালার্জির ওষুধ",
     "অ্যালার্জি, হাঁচি ও সর্দিতে\nচুলকানি ও চামড়ার অ্যালার্জিতে",
     COMMON_HOW,
     "ঘুম ঘুম ভাব\nমুখ শুকিয়ে যাওয়া",
     "ঘুম পেতে পারে, তাই খাওয়ার পর গাড়ি চালানোয় সতর্ক থাকুন।\nকিডনির রোগ থাকলে আগে ডাক্তারকে জানান।",
     [("Alatrol", "এলাট্রল", "Square", "10 mg", "Tablet", "3.00", "1 tablet", False),
      ("Atrizin", "অ্যাট্রিজিন", "Opsonin", "10 mg", "Tablet", "2.50", "1 tablet", False)]),
    ("Fexofenadine", "ফেক্সোফেনাডিন", "Antihistamine", "অ্যালার্জির ওষুধ",
     "অ্যালার্জি, হাঁচি ও সর্দিতে\nচুলকানি ও চামড়ার অ্যালার্জিতে",
     f"{COMMON_HOW}\nফলের রসের সাথে না খেয়ে পানি দিয়ে খান।",
     "মাথাব্যথা\nবমি ভাব",
     "কিডনির রোগ থাকলে আগে ডাক্তারকে জানান।",
     [("Fexo", "ফেক্সো", "Square", "120 mg", "Tablet", "9.00", "1 tablet", True),
      ("Fenadin", "ফেনাডিন", "Renata", "120 mg", "Tablet", "8.00", "1 tablet", False)]),
    ("Montelukast", "মন্টিলুকাস্ট", "Asthma and allergy", "হাঁপানি ও অ্যালার্জির ওষুধ",
     "হাঁপানি প্রতিরোধে\nঅ্যালার্জিজনিত সর্দিতে",
     f"{COMMON_HOW}\nহঠাৎ শ্বাসকষ্টের সময় এটি কাজ করে না।",
     "মাথাব্যথা\nপেটব্যথা",
     "মেজাজ বা আচরণে পরিবর্তন দেখলে দ্রুত ডাক্তারকে জানান।",
     [("Monas", "মোনাস", "ACME", "10 mg", "Tablet", "15.00", "1 tablet", True),
      ("Montene", "মন্টিন", "Beximco", "10 mg", "Tablet", "14.00", "1 tablet", False),
      ("Provair", "প্রোভেয়ার", "Healthcare", "10 mg", "Tablet", "13.00", "1 tablet", False)]),
    ("Azithromycin", "অ্যাজিথ্রোমাইসিন", "Antibiotic", "অ্যান্টিবায়োটিক",
     "ডাক্তার নির্ধারিত ব্যাকটেরিয়াজনিত সংক্রমণে",
     "শুধু ডাক্তারের ব্যবস্থাপত্র অনুযায়ী খান।\nভালো লাগলেও পুরো কোর্স শেষ করুন।",
     "ডায়রিয়া, বমি ভাব\nপেটব্যথা",
     "ডাক্তারের পরামর্শ ছাড়া অ্যান্টিবায়োটিক খাবেন না।\nহৃদরোগ বা লিভারের রোগ থাকলে আগে ডাক্তারকে জানান।",
     [("Zimax", "জিম্যাক্স", "Square", "500 mg", "Tablet", "40.00", "1 tablet", True),
      ("Azithrocin", "অ্যাজিথ্রোসিন", "Beximco", "500 mg", "Tablet", "38.00", "1 tablet", False),
      ("Zithrin", "জিথ্রিন", "Renata", "500 mg", "Tablet", "35.00", "1 tablet", False)]),
    ("Amoxicillin", "অ্যামোক্সিসিলিন", "Antibiotic", "অ্যান্টিবায়োটিক",
     "ডাক্তার নির্ধারিত ব্যাকটেরিয়াজনিত সংক্রমণে",
     "শুধু ডাক্তারের ব্যবস্থাপত্র অনুযায়ী খান।\nভালো লাগলেও পুরো কোর্স শেষ করুন।",
     "ডায়রিয়া, বমি ভাব\nচামড়ায় র‍্যাশ",
     "পেনিসিলিনে অ্যালার্জি থাকলে খাবেন না।\nশ্বাসকষ্ট বা মুখ ফুলে গেলে সাথে সাথে হাসপাতালে যান।",
     [("Moxacil", "মক্সাসিল", "Square", "500 mg", "Capsule", "6.50", "1 capsule", False),
      ("Tycil", "টাইসিল", "Beximco", "500 mg", "Capsule", "6.00", "1 capsule", False)]),
    ("Cefixime", "সেফিক্সিম", "Antibiotic", "অ্যান্টিবায়োটিক",
     "ডাক্তার নির্ধারিত ব্যাকটেরিয়াজনিত সংক্রমণে",
     "শুধু ডাক্তারের ব্যবস্থাপত্র অনুযায়ী খান।\nভালো লাগলেও পুরো কোর্স শেষ করুন।",
     "ডায়রিয়া\nপেটব্যথা, বমি ভাব",
     "পেনিসিলিন বা সেফালোস্পোরিনে অ্যালার্জি থাকলে আগে ডাক্তারকে জানান।",
     [("Cef-3", "সেফ-থ্রি", "Square", "200 mg", "Capsule", "35.00", "1 capsule", False),
      ("Denvar", "ডেনভার", "Incepta", "200 mg", "Capsule", "33.00", "1 capsule", False)]),
    ("Ciprofloxacin", "সিপ্রোফ্লক্সাসিন", "Antibiotic", "অ্যান্টিবায়োটিক",
     "ডাক্তার নির্ধারিত ব্যাকটেরিয়াজনিত সংক্রমণে",
     "শুধু ডাক্তারের ব্যবস্থাপত্র অনুযায়ী খান।\nদুধ বা এন্টাসিডের সাথে একসাথে খাবেন না।",
     "বমি ভাব, ডায়রিয়া\nমাথা ঘোরা",
     "গোড়ালি বা মাংসপেশিতে ব্যথা হলে খাওয়া বন্ধ করে ডাক্তারকে জানান।\nগর্ভবতী হলে বা শিশুদের ক্ষেত্রে আগে ডাক্তারের পরামর্শ নিন।",
     [("Ciprocin", "সিপ্রোসিন", "Square", "500 mg", "Tablet", "15.00", "1 tablet", False),
      ("Neofloxin", "নিওফ্লক্সিন", "Beximco", "500 mg", "Tablet", "14.00", "1 tablet", False)]),
    ("Metronidazole", "মেট্রোনিডাজল", "Antibiotic and antiprotozoal", "অ্যান্টিবায়োটিক ও আমাশয়ের ওষুধ",
     "ডাক্তার নির্ধারিত আমাশয় ও কিছু সংক্রমণে",
     "শুধু ডাক্তারের ব্যবস্থাপত্র অনুযায়ী খান।\nখাবারের পর খেলে পেটের অস্বস্তি কম হয়।",
     "মুখে ধাতব স্বাদ\nবমি ভাব",
     "খাওয়ার সময় মদ্যপান করবেন না।\nগর্ভবতী হলে আগে ডাক্তারকে জানান।",
     [("Filmet", "ফিলমেট", "Beximco", "400 mg", "Tablet", "1.50", "1 tablet", False),
      ("Metryl", "মেট্রিল", "Opsonin", "400 mg", "Tablet", "1.30", "1 tablet", False)]),
    ("Amlodipine", "অ্যামলোডিপিন", "Blood pressure", "উচ্চ রক্তচাপের ওষুধ",
     "উচ্চ রক্তচাপে\nহৃদরোগজনিত বুকব্যথায়",
     f"{COMMON_HOW}\nপ্রতিদিন একই সময়ে খান। নিজে থেকে বন্ধ করবেন না।",
     "পা বা গোড়ালি ফুলে যাওয়া\nমাথাব্যথা, মুখ লাল হওয়া",
     "হঠাৎ বন্ধ করার আগে ডাক্তারের সাথে কথা বলুন।\nমাথা ঘোরা বা অজ্ঞান ভাব হলে ডাক্তারকে জানান।",
     [("Camlodin", "ক্যামলোডিন", "Square", "5 mg", "Tablet", "5.00", "1 tablet", True),
      ("Amdocal", "অ্যামডোক্যাল", "Beximco", "5 mg", "Tablet", "4.50", "1 tablet", False)]),
    ("Losartan Potassium", "লোসারটান পটাশিয়াম", "Blood pressure", "উচ্চ রক্তচাপের ওষুধ",
     "উচ্চ রক্তচাপে",
     f"{COMMON_HOW}\nপ্রতিদিন একই সময়ে খান। নিজে থেকে বন্ধ করবেন না।",
     "মাথা ঘোরা\nরক্তে পটাশিয়াম বেড়ে যাওয়া",
     "গর্ভাবস্থায় খাওয়া যাবে না; গর্ভধারণ করলে সাথে সাথে ডাক্তারকে জানান।\nকিডনির রোগ থাকলে আগে ডাক্তারকে জানান।",
     [("Angilock", "অ্যাঞ্জিলক", "Square", "50 mg", "Tablet", "8.00", "1 tablet", False),
      ("Osartil", "ওসারটিল", "Incepta", "50 mg", "Tablet", "7.50", "1 tablet", False)]),
    ("Metformin Hydrochloride", "মেটফরমিন", "Diabetes", "ডায়াবেটিসের ওষুধ",
     "টাইপ ২ ডায়াবেটিসে রক্তের চিনি নিয়ন্ত্রণে",
     f"{COMMON_HOW}\nখাবারের সাথে বা পরে খেলে পেটের সমস্যা কম হয়।",
     "বমি ভাব, ডায়রিয়া\nপেটের অস্বস্তি",
     "কিডনি বা লিভারের গুরুতর রোগ থাকলে আগে ডাক্তারকে জানান।\nঅপারেশন বা এক্স-রে ডাই পরীক্ষার আগে ডাক্তারকে জানান যে আপনি এটি খাচ্ছেন।",
     [("Comet", "কমেট", "Square", "500 mg", "Tablet", "4.00", "1 tablet", True),
      ("Informet", "ইনফরমেট", "Incepta", "500 mg", "Tablet", "3.50", "1 tablet", False)]),
    ("Atorvastatin", "অ্যাটোরভাস্টাটিন", "Cholesterol", "কোলেস্টেরলের ওষুধ",
     "রক্তে কোলেস্টেরল কমাতে\nহৃদরোগের ঝুঁকি কমাতে",
     COMMON_HOW,
     "মাংসপেশিতে ব্যথা\nপেটের অস্বস্তি",
     "অকারণে মাংসপেশিতে তীব্র ব্যথা হলে ডাক্তারকে জানান।\nগর্ভাবস্থায় বা লিভারের সক্রিয় রোগে খাওয়া ঠিক নয়।",
     [("Atova", "অ্যাটোভা", "Beximco", "10 mg", "Tablet", "12.00", "1 tablet", False),
      ("Anzitor", "অ্যানজিটর", "Square", "10 mg", "Tablet", "11.00", "1 tablet", False)]),
    ("Salbutamol", "সালবিউটামল", "Asthma and allergy", "হাঁপানি ও অ্যালার্জির ওষুধ",
     "হাঁপানি ও শ্বাসকষ্টে",
     COMMON_HOW,
     "হাত কাঁপা\nবুক ধড়ফড় করা",
     "ওষুধে শ্বাসকষ্ট না কমলে দ্রুত হাসপাতালে যান।\nহৃদরোগ থাকলে আগে ডাক্তারকে জানান।",
     [("Sultolin", "সালটোলিন", "Square", "2 mg/5 ml", "Syrup", "28.00", "100 ml bottle", False),
      ("Azmasol", "অ্যাজমাসল", "Beximco", "2 mg/5 ml", "Syrup", "26.00", "100 ml bottle", False)]),
    ("Domperidone", "ডমপেরিডন", "Anti-nausea", "বমি ভাব কমানোর ওষুধ",
     "বমি ও বমি ভাবে\nপেট ফাঁপায়",
     f"{COMMON_HOW}\nসাধারণত খাবারের আগে খেতে হয়।",
     "মুখ শুকিয়ে যাওয়া\nমাথাব্যথা",
     "হৃদরোগ থাকলে আগে ডাক্তারকে জানান।\nডাক্তারের পরামর্শ ছাড়া দীর্ঘদিন খাবেন না।",
     [("Motigut", "মোটিগাট", "Square", "10 mg", "Tablet", "3.00", "1 tablet", False),
      ("Omidon", "ওমিডন", "Incepta", "10 mg", "Tablet", "2.80", "1 tablet", False)]),
    ("Ibuprofen", "আইবুপ্রোফেন", "Pain relief and fever", "ব্যথা ও জ্বর উপশম",
     "ব্যথা ও প্রদাহ কমাতে\nজ্বর কমাতে",
     f"{COMMON_HOW}\nখাবারের পরে খান।",
     "পেটের অস্বস্তি, বুক জ্বালা\nবমি ভাব",
     "পাকস্থলীর ক্ষত, কিডনির রোগ বা হাঁপানি থাকলে আগে ডাক্তারকে জানান।\nগর্ভাবস্থায় ডাক্তারের পরামর্শ ছাড়া খাবেন না।\nডেঙ্গু সন্দেহ হলে খাবেন না।",
     [("Flamex", "ফ্ল্যামেক্স", "Square", "400 mg", "Tablet", "3.00", "1 tablet", False),
      ("Inflam", "ইনফ্ল্যাম", "Opsonin", "400 mg", "Tablet", "2.50", "1 tablet", False)]),
    ("Aspirin", "অ্যাসপিরিন", "Blood thinner", "রক্ত জমাট প্রতিরোধের ওষুধ",
     "ডাক্তারের পরামর্শে হৃদরোগ ও স্ট্রোকের ঝুঁকি কমাতে",
     f"{COMMON_HOW}\nখাবারের পরে খান।",
     "পেটের অস্বস্তি\nসহজে রক্তপাত বা কালশিটে",
     "ডেঙ্গু সন্দেহ হলে খাবেন না।\n১৬ বছরের কম বয়সীদের ডাক্তারের পরামর্শ ছাড়া দেবেন না।\nপাকস্থলীর ক্ষত বা রক্তপাতের সমস্যা থাকলে আগে ডাক্তারকে জানান।",
     [("Ecosprin", "ইকোস্প্রিন", "ACI", "75 mg", "Tablet", "1.00", "1 tablet", False),
      ("Bexiprin", "বেক্সিপ্রিন", "Beximco", "75 mg", "Tablet", "0.80", "1 tablet", False)]),
]

SOURCE = "Sample text for testing, not from an official leaflet"


class Command(BaseCommand):
    help = "Add (or with --clear, remove) the sample medicines used for testing."

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Remove all rows marked as sample data.")
        parser.add_argument("--force", action="store_true", help="Allow adding sample data when DEBUG is off.")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["clear"]:
            self._clear()
            return
        if not (settings.DEBUG or options["force"]):
            raise CommandError("DEBUG is off, so this may be the live site. Sample prices are invented: use --force if you are sure.")

        makers = {
            key: Manufacturer.objects.get_or_create(name=name, defaults={"name_bn": bn, "is_sample": True})[0]
            for key, (name, bn) in MANUFACTURERS.items()
        }
        forms = {
            name: DosageForm.objects.get_or_create(name=name, defaults={"name_bn": bn, "is_sample": True})[0]
            for name, bn in FORMS.items()
        }
        count = 0
        for name, name_bn, cls, cls_bn, uses, how, side, warn, brands in GENERICS:
            drug_class = DrugClass.objects.get_or_create(name=cls, defaults={"name_bn": cls_bn, "is_sample": True})[0]
            generic = Generic.objects.get_or_create(name=name, defaults={
                "name_bn": name_bn, "drug_class": drug_class, "uses": uses, "how_to_take": how,
                "side_effects": side, "warnings": warn, "source": SOURCE, "is_sample": True,
            })[0]
            for brand, brand_bn, maker, strength, form, price, unit, popular in brands:
                _, created = Medicine.objects.get_or_create(
                    brand_name=brand, strength=strength, dosage_form=forms[form], manufacturer=makers[maker],
                    defaults={
                        "brand_name_bn": brand_bn, "generic": generic, "price": Decimal(price), "price_unit": unit,
                        "is_popular": popular, "is_sample": True,
                    },
                )
                count += created
        self.stdout.write(self.style.SUCCESS(f"Added {count} sample medicines ({len(GENERICS)} generics)."))

    def _clear(self):
        medicines, _ = Medicine.objects.filter(is_sample=True).delete()
        # Keep a sample generic or company if a medicine you imported now uses it.
        Generic.objects.filter(is_sample=True, medicines__isnull=True).delete()
        for model in (Manufacturer, DosageForm):
            model.objects.filter(is_sample=True, medicines__isnull=True).delete()
        DrugClass.objects.filter(is_sample=True, generics__isnull=True).delete()
        self.stdout.write(self.style.SUCCESS(f"Removed {medicines} sample medicines."))
