from django.db import migrations

SPECIES = [(1, "dog", "Dog"), (2, "cat", "Cat"), (3, "bird", "Bird")]  # pks used by fixtures


def add(apps, schema_editor):
    Species = apps.get_model("care", "Species")
    for pk, code, name in SPECIES:
        Species.objects.update_or_create(pk=pk, defaults={"code": code, "name": name})


class Migration(migrations.Migration):
    dependencies = [("care", "0001_initial")]
    operations = [migrations.RunPython(add, migrations.RunPython.noop)]
