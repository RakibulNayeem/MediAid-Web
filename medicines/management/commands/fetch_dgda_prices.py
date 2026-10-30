"""Collect prices from DGDA's public price pages, into a CSV that `import_csv medicines` reads.

There is one page per medicine, so this waits between requests to go easy on a government server.
It can be stopped at any time: run it again with the same file and it carries on where it left off.

    python manage.py fetch_dgda_prices data/dgda_prices.csv --popular-only
    python manage.py fetch_dgda_prices data/dgda_prices.csv
    python manage.py import_csv medicines data/dgda_prices.csv
"""
import csv
import html
import json
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from medicines.popular import POPULAR_MEDICINES
from medicines.text import normalize, normalize_strength

from .convert_dgda import OUTPUT_COLUMNS, convert_rows

BASE_URL = "http://180.211.137.202:9310/Allopathic/"
USER_AGENT = "MediAid-price-import/1.0"
PAGE_SIZE = 500
MAX_FAILURES_IN_A_ROW = 5
PRICE_COLUMNS = OUTPUT_COLUMNS + ["price", "price_unit", "price_updated_on"]
AMOUNT_PACK = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(ml|gm|mg|g|l)\b", re.IGNORECASE)
PRICE = re.compile(r"(\d[\d,]*(?:\.\d+)?)")


def parse_price_page(page):
    """Returns [(pack size, unit price)]. Raises ValueError if this isn't a price page at all."""
    if "Unit Price" not in page:
        raise ValueError("not a price page")
    page = re.sub(r"(?is)<(style|script).*?</\1>", "", page)
    cells = [html.unescape(re.sub(r"<[^>]+>", "", cell)).strip() for cell in re.findall(r"(?is)<td[^>]*>(.*?)</td>", page)]
    rows = []
    for index in range(0, len(cells) - 2, 3):
        match = PRICE.search(cells[index + 2])
        if match:
            rows.append((" ".join(cells[index + 1].split()), match.group(1).replace(",", "")))
    return rows


def choose_price(rows, form):
    """Pick one (price, unit) for a medicine, or None. The unit decides which brands can be compared.

    DGDA's "unit price" is per tablet or capsule, but for bottles and tubes it is the whole pack.
    A medicine with several pack sizes uses its smallest, the size most brands have in common.
    """
    options = []
    for pack, text in rows:
        try:
            price = Decimal(text)
        except InvalidOperation:
            continue
        if price > 0:  # a zero means no real price is listed
            options.append((pack, price))
    if not options:
        return None
    form = form.lower()
    amounts = [(Decimal(m.group(1)), m.group(2).lower(), price) for pack, price in options if (m := AMOUNT_PACK.match(pack))]
    if amounts:
        amount, unit, price = min(amounts, key=lambda item: item[0])
        return price, f"{amount.normalize():f} {unit}"
    if "tablet" in form:
        return options[0][1], "1 tablet"
    if "capsule" in form or "cozycap" in form:
        return options[0][1], "1 capsule"
    pack, price = options[0]
    return price, pack.lower()[:50]  # e.g. a vial with water: only the same pack can be compared


def _get(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", "replace")


class Command(BaseCommand):
    help = "Collect medicine prices from DGDA's price pages."

    def add_arguments(self, parser):
        parser.add_argument("output")
        parser.add_argument("--delay", type=float, default=1.0, help="Seconds to wait between requests.")
        parser.add_argument("--popular-only", action="store_true", help="Only medicines comparable with those in popular.py.")

    def handle(self, *args, **options):
        output = Path(options["output"])
        self.delay = options["delay"]
        catalog = self._catalog(output.with_suffix(".catalog.json"))
        rows, _skipped = convert_rows(catalog)
        rows = self._in_priority_order(rows, options["popular_only"])

        done = set()
        if output.exists():
            with output.open(encoding="utf-8", newline="") as file:
                done = {self._key(row) for row in csv.DictReader(file)}
        todo = [row for row in rows if self._key(row) not in done]
        self.stdout.write(f"{len(todo)} to collect, {len(done)} already done.", ending="\n")

        is_new = not output.exists()
        failures = priced = 0
        with output.open("a", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, PRICE_COLUMNS, extrasaction="ignore")
            if is_new:
                writer.writeheader()
            for count, row in enumerate(todo, 1):
                time.sleep(self.delay)
                try:
                    choice = choose_price(parse_price_page(_get(BASE_URL + row["dgda_link"])), row["dosage_form"])
                except (OSError, ValueError) as exc:
                    failures += 1
                    self.stderr.write(f"Failed {row['brand_name']}: {exc}")
                    if failures >= MAX_FAILURES_IN_A_ROW:
                        raise CommandError("Too many failures in a row, so stopping. Run again later to carry on.")
                    time.sleep(self.delay * 30)  # give the server room
                    continue
                failures = 0
                if choice:
                    priced += 1
                    row["price"], row["price_unit"] = choice
                    row["price_updated_on"] = date.today().isoformat()
                writer.writerow(row)
                file.flush()
                if count % 100 == 0:
                    self.stdout.write(f"{count}/{len(todo)} checked, {priced} with a price.")
        self.stdout.write(self.style.SUCCESS(f"Finished: {len(todo)} checked, {priced} with a price."))

    def _key(self, row):
        return (normalize(row["brand_name"]), normalize_strength(row["strength"]), normalize(row["dosage_form"]), normalize(row["manufacturer"]))

    def _catalog(self, path):
        """The list of medicines with the link to each price page. Saved, so it's only fetched once."""
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        catalog, start, total = [], 0, 1
        while start < total:
            time.sleep(self.delay)
            data = json.loads(_get(f"{BASE_URL}Medicine_Information_Ajax.php?action=list&draw=1&start={start}&length={PAGE_SIZE}"))
            total = data["recordsTotal"]
            for row in data["data"]:
                link = re.search(r'href="([^"]+)"', row[6])
                catalog.append({
                    "Company": row[1], "Trade Name": row[2], "Generic Name With Strength": row[3],
                    "Dosage Form": row[4], "DAR No": row[5], "link": html.unescape(link.group(1)) if link else "",
                })
            start += PAGE_SIZE
            self.stdout.write(f"Medicine list: {len(catalog)}/{total}")
        path.write_text(json.dumps(catalog), encoding="utf-8")
        return catalog

    def _in_priority_order(self, rows, popular_only):
        """Brands comparable with popular medicines first, then generics with the most brands."""
        rows = [row for row in rows if row.get("dgda_link")]
        wanted = {(normalize(b), normalize_strength(s), normalize(f)) for b, s, f in POPULAR_MEDICINES}
        groups = {
            (normalize(row["generic"]), normalize_strength(row["strength"]), normalize(row["dosage_form"]))
            for row in rows
            if (normalize(row["brand_name"]), normalize_strength(row["strength"]), normalize(row["dosage_form"])) in wanted
        }

        def in_group(row):
            return (normalize(row["generic"]), normalize_strength(row["strength"]), normalize(row["dosage_form"])) in groups

        if popular_only:
            return [row for row in rows if in_group(row)]
        brand_counts = Counter(normalize(row["generic"]) for row in rows)
        return sorted(rows, key=lambda row: (not in_group(row), -brand_counts[normalize(row["generic"])]))
