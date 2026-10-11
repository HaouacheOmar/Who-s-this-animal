from django.contrib.postgres.fields import ArrayField, IntegerRangeField
from django.core.exceptions import ValidationError
from django.db import models

SIZE_CLASSES = [(s, s) for s in ("toy", "small", "medium", "large", "giant")]


class Species(models.Model):
    id = models.SmallAutoField(primary_key=True)
    code = models.CharField(max_length=10, unique=True, choices=[("dog", "dog"), ("cat", "cat"), ("bird", "bird")])
    name = models.CharField(max_length=30)

    class Meta:
        db_table = "species"

    def __str__(self):
        return self.name


class Breed(models.Model):
    species = models.ForeignKey(Species, on_delete=models.RESTRICT, related_name="breeds")
    model_label = models.CharField(max_length=80, unique=True)
    name = models.CharField(max_length=100)
    origin = models.CharField(max_length=100, blank=True)
    size_class = models.CharField(max_length=10, choices=SIZE_CLASSES, null=True, blank=True)
    adult_weight_min_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    adult_weight_max_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    adult_age_months = models.PositiveSmallIntegerField(default=12)
    life_expectancy_years = IntegerRangeField(null=True, blank=True)
    temperament = models.TextField(blank=True)
    exercise_min_per_day = models.PositiveSmallIntegerField(null=True, blank=True)
    grooming = models.TextField(blank=True)
    health_notes = models.TextField(blank=True)
    foods_to_avoid = ArrayField(models.CharField(max_length=60), default=list, blank=True)
    recommended_food_type = models.JSONField(default=dict, blank=True)  # {"young": "...", "adult": "...", "senior": "..."}
    meals_per_day = models.JSONField()  # {"young": 3, "adult": 2, "senior": 2}
    routine = models.JSONField()  # {"adult": [{"time", "activity", "duration_min", "category"}], ...}
    daily_food_g_min = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    daily_food_g_max = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    reviewed = models.BooleanField(default=False)

    class Meta:
        db_table = "breeds"
        constraints = [
            models.CheckConstraint(condition=models.Q(adult_weight_min_kg__gt=0) | models.Q(adult_weight_min_kg=None),
                                   name="breeds_weight_min_pos"),
            models.CheckConstraint(condition=models.Q(adult_weight_max_kg__gte=models.F("adult_weight_min_kg"))
                                   | models.Q(adult_weight_max_kg=None), name="breeds_weight_max_gte_min"),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        # A CHECK can't read species.code, so the per-species rule lives here (DATABASE_SCHEMA.md).
        if self.species.code == "bird":
            if self.daily_food_g_min is None or self.daily_food_g_max is None:
                raise ValidationError("Birds need daily_food_g_min and daily_food_g_max.")
        elif self.adult_weight_min_kg is None or self.adult_weight_max_kg is None:
            raise ValidationError("Dogs and cats need adult_weight_min_kg and adult_weight_max_kg.")


class FoodProduct(models.Model):
    species = models.ForeignKey(Species, on_delete=models.RESTRICT, related_name="foods")
    brand = models.CharField(max_length=60)
    name = models.CharField(max_length=120)
    food_type = models.CharField(max_length=10, choices=[(t, t) for t in ("dry", "wet", "seed", "pellet")])
    life_stage = models.CharField(max_length=10, choices=[(t, t) for t in ("young", "adult", "senior", "all")])
    size_class = models.CharField(max_length=10, choices=SIZE_CLASSES, null=True, blank=True)
    kcal_per_100g = models.DecimalField(max_digits=6, decimal_places=1)
    where_to_find = models.TextField(blank=True)
    price_dzd_approx = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = "food_products"
        constraints = [
            models.UniqueConstraint(fields=["brand", "name"], name="food_products_brand_name_uniq"),
            models.CheckConstraint(condition=models.Q(kcal_per_100g__gt=0), name="food_products_kcal_pos"),
        ]

    def __str__(self):
        return f"{self.brand} {self.name}"


class CareText(models.Model):
    breed = models.ForeignKey(Breed, on_delete=models.CASCADE)
    profile_hash = models.CharField(max_length=64)
    content = models.TextField()
    llm_model = models.CharField(max_length=60)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "care_texts"
        constraints = [models.UniqueConstraint(fields=["breed", "profile_hash"], name="care_texts_breed_hash_uniq")]
