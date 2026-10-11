from django.conf import settings
from django.db import models
from django.db.models.functions import Now


class Pet(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pets")
    breed = models.ForeignKey("care.Breed", on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=60)
    birth_date = models.DateField()
    sex = models.CharField(max_length=7, choices=[(s, s) for s in ("male", "female", "unknown")], default="unknown")
    neutered = models.BooleanField(default=False)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2)
    activity_level = models.CharField(max_length=6, choices=[(a, a) for a in ("low", "normal", "high")],
                                      default="normal")
    photo = models.ImageField(upload_to="pets/", max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pets"
        indexes = [models.Index(fields=["owner", "name"])]
        constraints = [
            models.CheckConstraint(condition=models.Q(weight_kg__gt=0), name="pets_weight_pos"),
            models.CheckConstraint(condition=models.Q(birth_date__lte=Now()), name="pets_birth_not_future"),
        ]

    def __str__(self):
        return self.name
