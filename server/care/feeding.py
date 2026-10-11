"""Feeding math (IMPLEMENTATION.md §7.2). Pure functions, no DB."""

ACTIVITY = {"low": 0.9, "normal": 1.0, "high": 1.2}


def life_stage(species: str, age_months: int, adult_age_months: int = 12, size_class: str | None = None) -> str:
    if species == "bird":
        return "adult"
    if species == "dog":
        senior = 60 if size_class == "giant" else 84
        young_until = adult_age_months
    else:  # cat
        senior, young_until = 132, 12
    if age_months < young_until:
        return "young"
    return "senior" if age_months >= senior else "adult"


def stage_factor(species: str, stage: str, age_months: int, neutered: bool) -> float:
    if species == "dog":
        if stage == "young":
            return 3.0 if age_months < 4 else 2.0
        if stage == "senior":
            return 1.4
        return 1.6 if neutered else 1.8
    if stage == "young":
        return 2.5
    if stage == "senior":
        return 1.1
    return 1.2 if neutered else 1.4


def rer(weight_kg: float) -> float:
    return 70 * weight_kg ** 0.75


def mer(species: str, weight_kg: float, stage: str, age_months: int, neutered: bool, activity: str = "normal") -> float:
    return rer(weight_kg) * stage_factor(species, stage, age_months, neutered) * ACTIVITY[activity]


def grams_per_day(kcal_per_day: float, kcal_per_100g: float) -> float:
    return kcal_per_day / (kcal_per_100g / 100)
