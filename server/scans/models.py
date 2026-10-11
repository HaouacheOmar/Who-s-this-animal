import uuid
from pathlib import Path

from django.conf import settings
from django.db import models

REJECT_REASONS = ["unreadable", "too_small", "blurry", "too_dark", "low_confidence"]


def scan_path(scan, filename):
    return f"scans/{scan.owner_id}/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"


class Scan(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="scans")
    pet = models.ForeignKey("pets.Pet", on_delete=models.SET_NULL, null=True, blank=True, related_name="scans")
    image = models.ImageField(upload_to=scan_path, max_length=255)
    breed = models.ForeignKey("care.Breed", on_delete=models.SET_NULL, null=True, blank=True)
    confidence = models.FloatField(null=True, blank=True)
    top_k = models.JSONField(default=list)
    is_possible_mix = models.BooleanField(default=False)
    reject_reason = models.CharField(max_length=20, null=True, blank=True, choices=[(r, r) for r in REJECT_REASONS])
    model_version = models.CharField(max_length=60, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "scans"
        indexes = [models.Index(fields=["owner", "-created_at"])]
        constraints = [
            models.CheckConstraint(condition=models.Q(breed=None) | models.Q(reject_reason=None),
                                   name="scans_recognized_xor_rejected"),
            models.CheckConstraint(condition=models.Q(confidence=None) | models.Q(confidence__gte=0, confidence__lte=1),
                                   name="scans_confidence_range"),
        ]

    def delete(self, *args, **kwargs):
        self.image.delete(save=False)  # DB cascades don't touch files
        return super().delete(*args, **kwargs)
