"""Build the curated care sheet (PRD §6) for a breed, averaged or personalised to a pet."""
from datetime import date

from django.db.models import Q

from .feeding import grams_per_day, life_stage, mer
from .models import Breed, FoodProduct

DISCLAIMER = "This is general guidance, not veterinary advice. Consult a vet for your pet's specific needs."


def age_months(birth_date: date, today: date | None = None) -> int:
    today = today or date.today()
    return (today.year - birth_date.year) * 12 + today.month - birth_date.month - (today.day < birth_date.day)


def pick(by_stage: dict, stage: str):
    return by_stage.get(stage, by_stage.get("adult"))


def care_sheet(breed: Breed, pet=None) -> dict:
    species = breed.species.code
    if pet:
        months = age_months(pet.birth_date)
        stage = life_stage(species, months, breed.adult_age_months, breed.size_class)
        weights, neutered, activity = [float(pet.weight_kg)], pet.neutered, pet.activity_level
    else:  # breed average: neutered adult, normal activity, across the adult weight range
        months, stage, neutered, activity = 36, "adult", True, "normal"
        weights = [float(breed.adult_weight_min_kg or 0), float(breed.adult_weight_max_kg or 0)]

    foods = FoodProduct.objects.filter(species=breed.species, life_stage__in=[stage, "all"]).filter(
        Q(size_class=breed.size_class) | Q(size_class=None)).order_by("brand", "name")

    if species == "bird":
        kcal = None
        grams = [float(breed.daily_food_g_min), float(breed.daily_food_g_max)]
        products = [product(f, None) for f in foods]
    else:
        kcal = [round(mer(species, w, stage, months, neutered, activity)) for w in weights]
        grams = None
        products = [product(f, kcal) for f in foods]

    return {
        "personalised": pet is not None,
        "life_stage": stage,
        "breed": {
            "id": breed.id,
            "name": breed.name,
            "species": species,
            "origin": breed.origin,
            "size_class": breed.size_class,
            "adult_weight_kg": [breed.adult_weight_min_kg, breed.adult_weight_max_kg],
            # int4range is stored half-open [12,16); send inclusive years [12, 15]
            "life_expectancy_years": [breed.life_expectancy_years.lower, breed.life_expectancy_years.upper - 1]
            if breed.life_expectancy_years else None,
            "temperament": breed.temperament,
            "exercise_min_per_day": breed.exercise_min_per_day,
            "grooming": breed.grooming,
            "health_notes": breed.health_notes,
        },
        "feeding": {
            "kcal_per_day": kcal,
            "bird_grams_per_day": grams,
            "meals_per_day": pick(breed.meals_per_day, stage),
            "recommended_food_type": pick(breed.recommended_food_type, stage),
            "products": products,
        },
        "foods_to_avoid": breed.foods_to_avoid,
        "routine": pick(breed.routine, stage) or [],
        "disclaimer": DISCLAIMER,
    }


def product(f: FoodProduct, kcal: list[int] | None) -> dict:
    return {
        "brand": f.brand,
        "name": f.name,
        "food_type": f.food_type,
        "grams_per_day": [round(grams_per_day(k, float(f.kcal_per_100g))) for k in kcal] if kcal else None,
        "where_to_find": f.where_to_find,
        "price_dzd_approx": f.price_dzd_approx,
    }
