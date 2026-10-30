from django.db import migrations

from medicines.text import sound_key


def fill_sound_text(apps, schema_editor):
    Medicine = apps.get_model("medicines", "Medicine")
    medicines = list(Medicine.objects.select_related("generic"))
    for medicine in medicines:
        words = f"{medicine.brand_name} {medicine.generic.name}".split()
        medicine.sound_text = " " + " ".join(key for key in map(sound_key, words) if key) + " "
    Medicine.objects.bulk_update(medicines, ["sound_text"], batch_size=500)
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(
            "CREATE INDEX IF NOT EXISTS medicine_sound_trgm_idx ON medicines_medicine USING gin (sound_text gin_trgm_ops)"
        )


def remove_index(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("DROP INDEX IF EXISTS medicine_sound_trgm_idx")


class Migration(migrations.Migration):
    dependencies = [("medicines", "0004_sound_text")]
    operations = [migrations.RunPython(fill_sound_text, remove_index)]
