from django.db import migrations


def add_trigram_index(apps, schema_editor):
    # Makes searching fast and enables spelling-mistake matching. PostgreSQL only: skipped on local SQLite.
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    schema_editor.execute(
        "CREATE INDEX IF NOT EXISTS medicine_search_trgm_idx ON medicines_medicine USING gin (search_text gin_trgm_ops)"
    )


def remove_trigram_index(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("DROP INDEX IF EXISTS medicine_search_trgm_idx")


class Migration(migrations.Migration):
    dependencies = [("medicines", "0001_initial")]
    operations = [migrations.RunPython(add_trigram_index, remove_trigram_index)]
