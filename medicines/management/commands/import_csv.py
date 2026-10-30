"""Load a CSV from your own computer. Use this for big files (Vercel refuses uploads over about 4.5 MB)."""
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from medicines.importer import IMPORTERS


class Command(BaseCommand):
    help = "Import medicines or generic information from a CSV file."

    def add_arguments(self, parser):
        parser.add_argument("kind", choices=sorted(IMPORTERS))
        parser.add_argument("path")
        parser.add_argument("--dry-run", action="store_true", help="Check the file without saving anything.")

    def handle(self, *args, **options):
        path = Path(options["path"])
        if not path.is_file():
            raise CommandError(f"File not found: {path}")
        result = IMPORTERS[options["kind"]](path.read_bytes(), dry_run=options["dry_run"])
        if not result.ok:
            for error in result.errors:
                self.stderr.write(error)
            raise CommandError(f"{len(result.errors)} problem(s) found. Nothing was saved.")
        verb = "Would save" if result.dry_run else "Saved"
        self.stdout.write(self.style.SUCCESS(f"{verb}: {result.created} new, {result.updated} updated, {result.unchanged} unchanged."))
