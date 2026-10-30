from decimal import Decimal
import csv
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.urls import reverse

from .importer import import_generics, import_medicines
from .management.commands.convert_dgda import OUTPUT_COLUMNS, convert_rows
from .management.commands.fetch_dgda_prices import choose_price, parse_price_page
from .models import DosageForm, Generic, Manufacturer, Medicine
from .search import matching_generics, search_medicines
from .text import bangla_to_latin, normalize, normalize_strength, sound_key


def make_medicine(brand, generic=None, strength="500 mg", form="Tablet", maker="Maker", price="2.00", unit="1 tablet", **extra):
    generic = generic or Generic.objects.get_or_create(name="Paracetamol", defaults={"name_bn": "প্যারাসিটামল"})[0]
    return Medicine.objects.create(
        brand_name=brand, generic=generic, strength=strength,
        dosage_form=DosageForm.objects.get_or_create(name=form)[0],
        manufacturer=Manufacturer.objects.get_or_create(name=maker)[0],
        price=Decimal(price) if price is not None else None, price_unit=unit, **extra,
    )


class TextTests(TestCase):
    def test_digits_and_case(self):
        self.assertEqual(normalize("  NAPA  ৫০০ "), "napa 500")

    def test_strength_spacing(self):
        self.assertEqual(normalize_strength("500 MG"), normalize_strength("500mg"))
        self.assertEqual(normalize_strength("৫০০ mg"), "500mg")

    def test_bangla_romanisation(self):
        self.assertEqual(bangla_to_latin("নাপা"), "napa")
        self.assertEqual(bangla_to_latin("প্যারাসিটামল"), "parasitaml")


class SearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.napa = make_medicine("Napa", brand_name_bn="নাপা")
        cls.ace = make_medicine("Ace")
        cls.other = make_medicine("Seclo", Generic.objects.create(name="Omeprazole", name_bn="ওমিপ্রাজল"), strength="20 mg", form="Capsule")

    def brands(self, query):
        return [m.brand_name for m in search_medicines(query)[0]]

    def test_brand_english_any_case(self):
        self.assertEqual(self.brands("NAPA"), ["Napa"])

    def test_brand_bangla(self):
        self.assertEqual(self.brands("নাপা"), ["Napa"])

    def test_generic_english_and_bangla(self):
        self.assertCountEqual(self.brands("paracetamol"), ["Napa", "Ace"])
        self.assertCountEqual(self.brands("প্যারাসিটামল"), ["Napa", "Ace"])

    def test_bangla_generic_without_bangla_name(self):
        make_medicine("Comet", Generic.objects.create(name="Metformin"), maker="Other")
        self.assertEqual(self.brands("মেটফরমিন"), ["Comet"])
        self.assertEqual([g.name for g in matching_generics("মেটফরমিন")], ["Metformin"])

    def test_brand_with_bangla_digits(self):
        self.assertEqual(self.brands("নাপা ৫০০"), ["Napa"])

    def test_bangla_query_finds_english_only_name(self):
        make_medicine("Rupa", maker="Other")
        self.assertEqual(self.brands("রুপা"), ["Rupa"])

    def test_bangla_query_finds_near_spelling(self):
        make_medicine("Cyclophos", Generic.objects.create(name="Cyclophosphamide"), maker="Other")
        self.assertEqual(self.brands("সেকলো"), ["Seclo"])

    def test_nonsense_finds_nothing(self):
        self.assertEqual(self.brands("qwxyz"), [])

    def test_plain_generic_listed_before_combinations(self):
        Generic.objects.create(name="Caffeine + Paracetamol")
        self.assertEqual(matching_generics("paracetamol")[0].name, "Paracetamol")

    def test_opening_vowel_spellings_match(self):
        make_medicine("Zimax", Generic.objects.create(name="Azithromycin"), maker="Other")
        self.assertEqual(self.brands("অ্যাজিথ্রোমাইসিন"), ["Zimax"])

    def test_matches_start_of_word_not_middle(self):
        self.assertEqual(self.brands("ace"), ["Ace"])

    def test_brand_match_ranks_before_generic_match(self):
        Generic.objects.create(name="Napaxin")
        make_medicine("Zzz", Generic.objects.get(name="Napaxin"))
        self.assertEqual(self.brands("napa"), ["Napa", "Zzz"])

    def test_empty_and_unknown(self):
        self.assertEqual(self.brands("   "), [])
        self.assertEqual(self.brands("qqqqqqqq"), [])

    def test_inactive_hidden(self):
        Medicine.objects.filter(pk=self.ace.pk).update(is_active=False)
        self.assertEqual(self.brands("ace"), [])

    def test_other_spellings_find_the_right_medicine_not_a_lookalike(self):
        make_medicine("Parasitin", Generic.objects.create(name="Mebendazole"), maker="Other")
        for query in ["paracitamol", "প্যারাসিটামোল"]:
            with self.subTest(query):
                results, was_fuzzy = search_medicines(query)
                self.assertFalse(was_fuzzy)
                self.assertCountEqual([m.brand_name for m in results], ["Napa", "Ace"])

    def test_sound_keys(self):
        self.assertEqual(sound_key("paracetamol"), sound_key("প্যারাসিটামল"))
        self.assertEqual(sound_key("seclo"), sound_key("সেকলো"))
        self.assertEqual(sound_key("metformin"), sound_key("মেটফরমিন"))

    def test_generic_shortcut(self):
        self.assertEqual([g.name for g in matching_generics("ওমিপ্রাজল")], ["Omeprazole"])

    def test_renaming_generic_updates_search(self):
        generic = Generic.objects.get(name="Omeprazole")
        generic.name_bn = "নতুননাম"
        generic.save()
        self.assertEqual(self.brands("নতুননাম"), ["Seclo"])

    def test_percent_and_quotes_are_harmless(self):
        self.assertEqual(self.brands("%"), [])
        self.brands("'; DROP TABLE medicines_medicine; --")
        self.assertEqual(Medicine.objects.count(), 3)


class SuggestTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.napa = make_medicine("Napa", brand_name_bn="নাপা")
        make_medicine("Seclo", Generic.objects.create(name="Omeprazole"), strength="20 mg", form="Capsule")

    def suggest(self, query):
        return self.client.get(reverse("medicines:suggest"), {"q": query}).json()["results"]

    def test_english_bangla_and_other_spellings(self):
        for query in ["nap", "নাপা", "paracitamol"]:
            with self.subTest(query):
                self.assertIn(self.napa.get_absolute_url(), [r["url"] for r in self.suggest(query)])

    def test_generic_is_suggested_with_its_page(self):
        results = self.suggest("paracetamol")
        self.assertEqual(results[0]["url"], self.napa.generic.get_absolute_url())

    def test_too_short_or_unknown_gives_nothing(self):
        self.assertEqual(self.suggest("n"), [])
        self.assertEqual(self.suggest("qwxyz"), [])

    def test_never_more_than_eight(self):
        for i in range(12):
            make_medicine(f"Napa{i:02}", maker=f"Maker{i}")
        self.assertEqual(len(self.suggest("napa")), 8)

    def test_home_page_search_box_is_wired_up(self):
        self.assertContains(self.client.get("/"), 'data-suggest-url="/medicines/suggest/"')


class AlternativesTests(TestCase):
    def setUp(self):
        self.napa = make_medicine("Napa", price="2.00", maker="A")
        self.ace = make_medicine("Ace", price="1.50", strength="500mg", maker="B")  # different spacing, same strength
        self.xpa = make_medicine("Xpa", price="1.00", maker="C")
        self.no_price = make_medicine("NoPrice", price=None, maker="D")
        self.other_strength = make_medicine("Big", strength="650 mg", maker="E")
        self.other_form = make_medicine("Liquid", form="Syrup", maker="F")

    def test_same_group_cheapest_first_and_no_price_last(self):
        self.assertEqual([m.brand_name for m in self.napa.alternatives()], ["Xpa", "Ace", "Napa", "NoPrice"])

    def test_savings_on_detail_page(self):
        response = self.client.get(self.napa.get_absolute_url())
        self.assertEqual(response.context["best_saving"], Decimal("1.00"))
        savings = {row["medicine"].brand_name: row["saving"] for row in response.context["alternatives"]}
        self.assertEqual(savings, {"Xpa": Decimal("1.00"), "Ace": Decimal("0.50"), "Napa": None, "NoPrice": None})

    def test_cheapest_is_marked_and_bars_compare_same_unit_only(self):
        make_medicine("Pack", price="0.50", unit="10 tablets", maker="G")
        rows = {r["medicine"].brand_name: r for r in self.client.get(self.napa.get_absolute_url()).context["alternatives"]}
        self.assertTrue(rows["Xpa"]["is_cheapest"])
        self.assertNotIn("is_cheapest", rows["Pack"])
        self.assertEqual((rows["Napa"]["bar"], rows["Xpa"]["bar"]), (100, 50))
        self.assertNotIn("bar", rows["NoPrice"])

    def test_cheapest_has_no_saving(self):
        response = self.client.get(self.xpa.get_absolute_url())
        self.assertIsNone(response.context["best_saving"])

    def test_different_pack_sizes_show_no_saving(self):
        syrup_small = make_medicine("Small", form="Suspension", price="30", unit="60 ml bottle", maker="A")
        syrup_big = make_medicine("Big2", form="Suspension", price="50", unit="100 ml bottle", maker="B")
        self.assertIsNone(syrup_big.saving_against(syrup_small))

    def test_missing_prices_are_not_called_no_cheaper_brand(self):
        response = self.client.get(self.xpa.get_absolute_url())
        self.assertContains(response, "সব দাম এখনো আমাদের কাছে নেই")
        self.assertNotContains(response, "এর চেয়ে কম দামের ব্র্যান্ড পাওয়া যায়নি")

    def test_long_alternative_lists_are_capped(self):
        for i in range(35):
            make_medicine(f"Extra{i:02}", maker=f"Maker{i}")
        response = self.client.get(self.napa.get_absolute_url())
        self.assertEqual(len(response.context["alternatives"]), 30)
        self.assertEqual(response.context["more_alternatives"], 9)

    def test_unknown_unit_shows_no_saving(self):
        one = make_medicine("One", form="Drop", price="30", unit="", maker="A")
        two = make_medicine("Two", form="Drop", price="20", unit="", maker="B")
        self.assertIsNone(one.saving_against(two))


class PageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_sample", "--force", stdout=StringIO())

    def test_home_is_bangla_by_default_even_with_english_browser(self):
        response = self.client.get("/", headers={"accept-language": "en-US"})
        self.assertContains(response, "ওষুধের নাম লিখুন — ব্র্যান্ড বা জেনেরিক")
        for label in ["রক্ত খুঁজুন", "অ্যাম্বুলেন্স", "হাসপাতাল", "ডাক্তার"]:
            self.assertContains(response, label)
        self.assertContains(response, "টাকা বাঁচান")
        self.assertContains(response, "emergency-fab")

    def test_logo_follows_the_language(self):
        home = self.client.get("/")
        self.assertContains(home, "mediaid-logo-bn-on-dark")
        self.assertContains(home, "mediaid-logo-bilingual-on-dark")
        self.assertContains(home, "favicon.ico")
        english = self.client.post(reverse("set_language"), {"language": "en", "next": "/"}, follow=True)
        self.assertContains(english, "mediaid-logo-en-on-dark")

    def test_english_toggle(self):
        response = self.client.post(reverse("set_language"), {"language": "en", "next": "/"}, follow=True)
        self.assertContains(response, "Brand or generic name")
        self.assertContains(response, "বাংলা")

    def test_medicine_page_has_disclaimer_and_sample_notice(self):
        medicine = Medicine.objects.get(brand_name="Napa")
        response = self.client.get(medicine.get_absolute_url())
        self.assertContains(response, "এটি চিকিৎসা পরামর্শ নয়")
        self.assertContains(response, "নমুনা তথ্য")
        self.assertContains(response, "৳ ১.২০")
        medicine.refresh_from_db()
        self.assertEqual(medicine.view_count, 1)

    def test_every_listing_page_loads(self):
        generic = Generic.objects.get(name="Paracetamol")
        maker = Manufacturer.objects.get(name="Square Pharmaceuticals")
        urls = [
            reverse("medicines:generic_list"), generic.get_absolute_url(), reverse("medicines:manufacturer_list"),
            maker.get_absolute_url(), reverse("medicines:drug_class_list"), generic.drug_class.get_absolute_url(),
            reverse("medicines:search") + "?q=napa", reverse("medicines:search") + "?q=", reverse("medicines:search") + "?q=qqqq",
            reverse("emergency:hub"), reverse("emergency:section", args=["blood"]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_unknown_pages_404(self):
        self.assertEqual(self.client.get("/medicines/nope/").status_code, 404)
        self.assertEqual(self.client.get("/emergency/nope/").status_code, 404)

    def test_search_escapes_query(self):
        response = self.client.get(reverse("medicines:search"), {"q": "<script>alert(1)</script>"})
        self.assertNotContains(response, "<script>alert(1)</script>")

    def test_clear_removes_only_sample_rows(self):
        mine = make_medicine("Mine", Generic.objects.create(name="Real"), maker="Real Maker")
        call_command("seed_sample", "--clear", stdout=StringIO())
        self.assertEqual(list(Medicine.objects.all()), [mine])
        self.assertFalse(Generic.objects.filter(is_sample=True).exists())


class SeedTests(TestCase):
    def test_seed_marks_everything_and_is_repeatable(self):
        call_command("seed_sample", "--force", stdout=StringIO())
        count = Medicine.objects.count()
        call_command("seed_sample", "--force", stdout=StringIO())
        self.assertEqual(Medicine.objects.count(), count)
        self.assertFalse(Medicine.objects.filter(is_sample=False).exists())
        self.assertEqual(Generic.objects.count(), 20)


HEADER = "brand_name,generic,strength,dosage_form,manufacturer,price,price_unit,price_updated_on,dgda_registration_no\n"


class ImportTests(TestCase):
    def test_creates_rows_and_accepts_excel_bom(self):
        data = ("﻿" + HEADER + "Napa,Paracetamol,500 mg,Tablet,Beximco,1.20,1 tablet,2026-10-30,R1\n").encode("utf-8")
        result = import_medicines(data)
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.created, 1)
        medicine = Medicine.objects.get()
        self.assertEqual(medicine.price, Decimal("1.20"))
        self.assertFalse(medicine.is_sample)
        self.assertEqual(medicine.strength_key, "500mg")
        self.assertTrue(medicine.slug)

    def test_dry_run_saves_nothing(self):
        result = import_medicines(HEADER + "Napa,Paracetamol,500 mg,Tablet,Beximco,1.20,,,\n", dry_run=True)
        self.assertEqual(result.created, 1)
        for model in (Medicine, Generic, Manufacturer, DosageForm):
            self.assertEqual(model.objects.count(), 0)

    def test_one_bad_row_saves_nothing(self):
        result = import_medicines(HEADER + "Napa,Paracetamol,500 mg,Tablet,Beximco,1.20,,,\nAce,Paracetamol,500 mg,Tablet,Square,abc,,,\n")
        self.assertFalse(result.ok)
        self.assertIn("Line 3", result.errors[0])
        self.assertEqual(Medicine.objects.count(), 0)
        self.assertEqual(Manufacturer.objects.count(), 0)

    def test_update_by_registration_number_and_blank_keeps_value(self):
        import_medicines(HEADER + "Napa,Paracetamol,500 mg,Tablet,Beximco,1.20,1 tablet,,R1\n")
        result = import_medicines(HEADER + "Napa Extra,Paracetamol,500 mg,Tablet,Beximco,,,,R1\n")
        self.assertEqual((result.created, result.updated), (0, 1))
        medicine = Medicine.objects.get()
        self.assertEqual(medicine.brand_name, "Napa Extra")
        self.assertEqual(medicine.price, Decimal("1.20"))
        self.assertEqual(medicine.price_unit, "1 tablet")

    def test_update_without_registration_number_ignores_case_and_spacing(self):
        import_medicines(HEADER + "Napa,Paracetamol,500 mg,Tablet,Beximco,1.20,,,\n")
        result = import_medicines(HEADER + "NAPA,PARACETAMOL,500MG,tablet,BEXIMCO,1.50,,,\n")
        self.assertEqual((result.created, result.updated), (0, 1))
        self.assertEqual(Medicine.objects.get().price, Decimal("1.50"))
        self.assertEqual(Generic.objects.count(), 1)

    def test_reimporting_same_file_changes_nothing(self):
        data = HEADER + "Napa,Paracetamol,500 mg,Tablet,Beximco,1.20,1 tablet,2026-10-30,R1\n"
        import_medicines(data)
        result = import_medicines(data)
        self.assertEqual((result.created, result.updated, result.unchanged), (0, 0, 1))

    def test_real_import_replaces_sample_flag(self):
        make_medicine("Napa", is_sample=True, maker="Beximco")
        import_medicines(HEADER + "Napa,Paracetamol,500 mg,Tablet,Beximco,1.50,,,\n")
        self.assertFalse(Medicine.objects.get().is_sample)

    def test_problems_are_reported_not_raised(self):
        cases = {
            "missing column": "brand_name,generic\nA,B\n",
            "unknown column": HEADER.strip() + ",colour\nA,B,1,T,M,1,,,,red\n",
            "empty cell": HEADER + ",Paracetamol,500 mg,Tablet,Beximco,1,,,\n",
            "negative price": HEADER + "A,B,1,T,M,-1,,,\n",
            "nan price": HEADER + "A,B,1,T,M,NaN,,,\n",
            "huge price": HEADER + "A,B,1,T,M,999999999,,,\n",
            "bad date": HEADER + "A,B,1,T,M,1,,30/10/2026,\n",
            "duplicate row": HEADER + "A,B,1,T,M,1,,,\nA,B,1,T,M,2,,,\n",
            "duplicate registration": HEADER + "A,B,1,T,M,1,,,R\nC,B,1,T,M,2,,,R\n",
            "too long": HEADER + "A,B," + "1" * 301 + ",T,M,1,,,\n",
            "empty file": "",
        }
        for name, data in cases.items():
            with self.subTest(name):
                self.assertFalse(import_medicines(data).ok)
                self.assertEqual(Medicine.objects.count(), 0)

    def test_not_utf8(self):
        self.assertIn("UTF-8", import_medicines(b"\xff\xfe\x00bad").errors[0])

    def test_generic_info_import(self):
        make_medicine("Napa")
        result = import_generics("generic,generic_bn,drug_class,uses,warnings\nparacetamol,নতুন,Pain,এক|দুই,সতর্ক\n")
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.updated, 1)
        generic = Generic.objects.get()
        self.assertEqual(generic.uses, "এক\nদুই")
        self.assertEqual(generic.drug_class.name, "Pain")
        self.assertIn("নতুন", Medicine.objects.get().search_text)

    def test_many_rows_with_same_slug_base(self):
        rows = "".join(f"Napa,Paracetamol,500 mg,Tablet,Maker {i},1,,,\n" for i in range(30))
        self.assertTrue(import_medicines(HEADER + rows).ok)
        self.assertEqual(Medicine.objects.values("slug").distinct().count(), 30)


class DgdaConvertTests(TestCase):
    def row(self, brand="Napa", generic="Paracetamol 500 mg", form="Tablet", maker="Beximco", dar="1"):
        return {"Trade Name": brand, "Generic Name With Strength": generic, "Dosage Form": form, "Company": maker, "DAR No": dar}

    def test_splits_generic_from_strength(self):
        cases = {
            "Paracetamol 500 mg": ("Paracetamol", "500 mg"),
            "Clonazepam .5 mg": ("Clonazepam", ".5 mg"),
            "Riboflavin + Vitamin B1 2 mg + 5 mg": ("Riboflavin + Vitamin B1", "2 mg + 5 mg"),
            "Calcium + Vitamin D3 500 mg + 200 IU": ("Calcium + Vitamin D3", "500 mg + 200 IU"),
            "Hypromellose .3 %": ("Hypromellose", ".3 %"),
        }
        for text, expected in cases.items():
            with self.subTest(text):
                rows, _ = convert_rows([self.row(generic=text)])
                self.assertEqual((rows[0]["generic"], rows[0]["strength"]), expected)

    def test_skips_what_should_not_be_listed(self):
        rows, skipped = convert_rows([
            self.row(form="Raw Materials"), self.row(form="Bolus"), self.row(brand="Acid (API)"),
            self.row(brand=""), self.row(generic="Pantoprazole"), self.row(dar="2"), self.row(dar="3"),
        ])
        self.assertEqual(len(rows), 1)
        self.assertEqual(skipped, {"missing details": 1, "no strength": 1, "not for people": 3, "duplicate": 1})

    def test_shared_registration_number_is_kept_once(self):
        rows, _ = convert_rows([self.row(dar="9"), self.row(brand="Ace", dar="9")])
        self.assertEqual([r["dgda_registration_no"] for r in rows], ["9", ""])

    def test_output_loads_through_the_importer(self):
        rows, _ = convert_rows([self.row(), self.row(brand="Ace", dar="2")])
        buffer = StringIO()
        writer = csv.DictWriter(buffer, OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
        result = import_medicines(buffer.getvalue())
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.created, 2)


class DgdaPriceTests(TestCase):
    PAGE = """<table><tr><th>SL</th><th>Pack Size</th><th>Unit Price</th></tr>
        <tr><td>1</td><td>10 x 10 in Blister Pack</td><td>4.01 TK</td></tr>
        <tr><td>2</td><td>5 x 10 in Blister Pack</td><td>1,200.50 TK</td></tr></table>"""

    def test_reads_the_price_table(self):
        self.assertEqual(parse_price_page(self.PAGE), [("10 x 10 in Blister Pack", "4.01"), ("5 x 10 in Blister Pack", "1200.50")])

    def test_price_without_a_leading_zero(self):
        page = "<th>Unit Price</th><td>1</td><td>50 x 10 in Blister Pack</td><td>.8 TK</td>"
        rows = parse_price_page(page)
        self.assertEqual(rows, [("50 x 10 in Blister Pack", ".8")])
        self.assertEqual(choose_price(rows, "Tablet"), (Decimal("0.8"), "1 tablet"))

    def test_empty_table_has_no_rows_but_another_page_is_an_error(self):
        self.assertEqual(parse_price_page("<th>Unit Price</th>"), [])
        with self.assertRaises(ValueError):
            parse_price_page("<h1>Server busy</h1>")

    def test_tablet_price_is_per_tablet(self):
        self.assertEqual(choose_price([("10 x 10 in Blister Pack", "4.01")], "Tablet"), (Decimal("4.01"), "1 tablet"))
        self.assertEqual(choose_price([("1 x 10 in Blister Pack", "3.45")], "Soft Gelatin Capsule"), (Decimal("3.45"), "1 capsule"))

    def test_bottle_uses_its_smallest_size(self):
        rows = [("100 ml in Bottle", "65.45"), ("60 ml in Bottle", "49.73")]
        self.assertEqual(choose_price(rows, "Suspension"), (Decimal("49.73"), "60 ml"))

    def test_other_packs_only_compare_with_the_same_pack(self):
        self.assertEqual(choose_price([("1 x 1 Vial With Water", "50")], "Injection"), (Decimal("50"), "1 x 1 vial with water"))

    def test_zero_or_missing_price_is_no_price(self):
        self.assertIsNone(choose_price([("10 in Blister Pack", "0")], "Tablet"))
        self.assertIsNone(choose_price([], "Tablet"))

    def test_sizes_are_written_plainly(self):
        self.assertEqual(choose_price([("100 ml in Bottle", "5")], "Syrup")[1], "100 ml")


class AdminImportTests(TestCase):
    def setUp(self):
        self.url = reverse("admin:medicines_import_csv")
        self.file = lambda: SimpleUploadedFile("m.csv", (HEADER + "Napa,Paracetamol,500 mg,Tablet,Beximco,1.20,,,\n").encode())

    def test_requires_staff_login(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)
        user = get_user_model().objects.create_user("plain", password="x")
        self.client.force_login(user)
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_staff_without_add_permission_refused(self):
        self.client.force_login(get_user_model().objects.create_user("staff", password="x", is_staff=True))
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_check_then_save(self):
        self.client.force_login(get_user_model().objects.create_superuser("boss", password="x"))
        response = self.client.post(self.url, {"kind": "medicines", "file": self.file(), "dry_run": "on"})
        self.assertContains(response, "looks good")
        self.assertEqual(Medicine.objects.count(), 0)
        response = self.client.post(self.url, {"kind": "medicines", "file": self.file()})
        self.assertContains(response, "Saved: 1 new")
        self.assertEqual(Medicine.objects.count(), 1)

    def test_admin_lists_load(self):
        call_command("seed_sample", "--force", stdout=StringIO())
        self.client.force_login(get_user_model().objects.create_superuser("boss", password="x"))
        for name in ["medicine", "generic", "manufacturer", "drugclass", "dosageform"]:
            with self.subTest(name):
                self.assertEqual(self.client.get(reverse(f"admin:medicines_{name}_changelist")).status_code, 200)
