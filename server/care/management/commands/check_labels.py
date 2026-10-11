import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from care.models import Breed


class Command(BaseCommand):
    help = "Fail unless the classifier labels in meta.json equal breeds.model_label."

    def handle(self, *args, **opts):
        model = set(json.loads(settings.MODEL_META.read_text())["labels"])
        db = set(Breed.objects.values_list("model_label", flat=True))
        if model != db:
            raise CommandError(f"missing breed rows: {sorted(model - db)}\nunknown to the model: {sorted(db - model)}")
        self.stdout.write(self.style.SUCCESS(f"{len(model)} labels match"))
