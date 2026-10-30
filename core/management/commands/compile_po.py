"""
Compile locale/*/LC_MESSAGES/django.po -> django.mo using only Python.

Same result as Django's `compilemessages`, but you don't need to install GNU gettext.
Usage: python manage.py compile_po
"""
import ast
import struct
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


def parse_po(path):
    """Return {msgid: msgstr}. Empty translations are left out, so the English text shows."""
    catalog, msgid, msgstr, field = {}, None, None, None

    def flush():
        if msgid is not None and msgstr:
            catalog[msgid] = msgstr

    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            if line.startswith("msgid "):
                flush()
                msgid, msgstr, field = ast.literal_eval(line[6:]), "", "msgid"
            elif line.startswith("msgstr "):
                msgstr, field = ast.literal_eval(line[7:]), "msgstr"
            elif line.startswith('"') and field == "msgid":
                msgid += ast.literal_eval(line)
            elif line.startswith('"') and field == "msgstr":
                msgstr += ast.literal_eval(line)
            else:
                raise ValueError("unexpected line")
        except (ValueError, SyntaxError, TypeError) as exc:
            raise CommandError(f"{path}:{lineno}: cannot parse ({exc}): {raw}")
    flush()
    return catalog


def write_mo(catalog, path):
    keys = sorted(catalog)
    ids = [k.encode("utf-8") for k in keys]
    strs = [catalog[k].encode("utf-8") for k in keys]
    count = len(keys)
    ids_table = 7 * 4
    strs_table = ids_table + count * 8
    data_start = strs_table + count * 8

    table, data = [], b""
    for item in ids + strs:
        table.append(struct.pack("<2I", len(item), data_start + len(data)))
        data += item + b"\0"
    header = struct.pack("<7I", 0x950412DE, 0, count, ids_table, strs_table, 0, 0)
    path.write_bytes(header + b"".join(table) + data)


class Command(BaseCommand):
    help = "Compile .po translation files to .mo without GNU gettext."

    def handle(self, *args, **options):
        found = False
        for locale_dir in settings.LOCALE_PATHS:
            for po in sorted(Path(locale_dir).glob("*/LC_MESSAGES/*.po")):
                found = True
                catalog = parse_po(po)
                write_mo(catalog, po.with_suffix(".mo"))
                self.stdout.write(f"{po} -> {po.with_suffix('.mo').name} ({len(catalog) - 1} strings)")
        if not found:
            raise CommandError("No .po files found in LOCALE_PATHS.")
