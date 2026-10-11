"""Draft fixtures/breeds.json with Ollama, one breed per classifier label (IMPLEMENTATION.md §7.1).

Resumable: labels already in the output file are skipped. A human must spot-check the result and set "reviewed".
Usage: python manage.py draft_breeds [--labels meta.json|manifest.csv] [--out fixtures/breeds.json]
"""
import csv
import json
import urllib.request
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

SPECIES_PK = {"dog": 1, "cat": 2, "bird": 3}  # fixed by care/migrations/0002_species
STAGES = ["young", "adult", "senior"]

ROUTINE_ITEM = {"type": "object", "required": ["time", "activity", "duration_min", "category"], "properties": {
    "time": {"type": "string", "description": "HH:MM"},
    "activity": {"type": "string"},
    "duration_min": {"type": "integer"},
    "category": {"enum": ["meal", "exercise", "play", "training", "grooming", "rest", "cage"]},
}}
by_stage = lambda schema: {"type": "object", "required": STAGES, "properties": {s: schema for s in STAGES}}

SCHEMA = {"type": "object", "required": [
    "name", "origin", "size_class", "adult_weight_min_kg", "adult_weight_max_kg", "adult_age_months",
    "life_expectancy_min", "life_expectancy_max", "temperament", "exercise_min_per_day", "grooming", "health_notes",
    "foods_to_avoid", "recommended_food_type", "meals_per_day", "routine", "daily_food_g_min", "daily_food_g_max"],
    "properties": {
        "name": {"type": "string"},
        "origin": {"type": "string"},
        "size_class": {"enum": ["toy", "small", "medium", "large", "giant", None]},
        "adult_weight_min_kg": {"type": "number"},
        "adult_weight_max_kg": {"type": "number"},
        "adult_age_months": {"type": "integer"},
        "life_expectancy_min": {"type": "integer"},
        "life_expectancy_max": {"type": "integer"},
        "temperament": {"type": "string"},
        "exercise_min_per_day": {"type": ["integer", "null"]},
        "grooming": {"type": "string", "description": "one or two sentences on coat care and how often"},
        "health_notes": {"type": "string"},
        "foods_to_avoid": {"type": "array", "items": {"type": "string"}},
        "recommended_food_type": by_stage({"type": "string"}),
        "meals_per_day": by_stage({"type": "integer"}),
        "routine": by_stage({"type": "array", "items": ROUTINE_ITEM}),
        "daily_food_g_min": {"type": ["number", "null"]},
        "daily_food_g_max": {"type": ["number", "null"]},
    }}


def read_labels(path: Path) -> list[str]:
    if path.suffix == ".csv":
        with open(path, newline="", encoding="utf-8") as f:
            return sorted({r["label"] for r in csv.DictReader(f)})
    return json.loads(path.read_text())["labels"]


def ask(label: str) -> dict:
    species, raw = label.split("_", 1)
    readable = raw.replace("_", " ")
    extra = ("For birds: size_class null, exercise_min_per_day null, and daily_food_g_min/max are grams of "
             "seed+pellet mix per day: pet birds eat roughly 10-25% of their body weight per day (a 35 g budgie "
             "about 4-8 g). Routine uses the 'cage' category for out-of-cage time and cleaning."
             if species == "bird" else
             "daily_food_g_min/max must be null (food grams are computed from calories). "
             "Young = puppy/kitten. Large and giant dogs become adult at 18-24 months.")
    prompt = (f"Give accurate, vet-consensus care data for the {species} breed/species '{readable}', as kept as a pet "
              f"in Algeria. {extra} Weights in kg for a healthy adult. Each routine is a typical full day "
              "(6-8 items, 24h clock) whose 'meal' items match meals_per_day for that stage exactly, with only "
              "activities this species really does. foods_to_avoid: specific foods toxic or harmful to this species. "
              "health_notes: common issues and when to see a vet. Answer with JSON only.")
    body = json.dumps({"model": settings.OLLAMA_MODEL, "prompt": prompt, "format": SCHEMA, "stream": False,
                       "think": False, "options": {"temperature": 0.2}}).encode()
    req = urllib.request.Request(f"{settings.OLLAMA_URL}/api/generate", body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(json.load(r)["response"])


def to_fixture(label: str, d: dict) -> dict:
    species = label.split("_", 1)[0]
    bird = species == "bird"
    return {"model": "care.breed", "fields": {
        "species": SPECIES_PK[species],
        "model_label": label,
        "name": d["name"],
        "origin": d["origin"],
        "size_class": None if bird else d["size_class"],
        "adult_weight_min_kg": d["adult_weight_min_kg"],
        "adult_weight_max_kg": max(d["adult_weight_max_kg"], d["adult_weight_min_kg"]),
        "adult_age_months": d["adult_age_months"],
        "life_expectancy_years": json.dumps({"lower": d["life_expectancy_min"],
                                             "upper": d["life_expectancy_max"] + 1, "bounds": "[)"}),
        "temperament": d["temperament"],
        "exercise_min_per_day": None if bird else d["exercise_min_per_day"],
        "grooming": d["grooming"],
        "health_notes": d["health_notes"],
        "foods_to_avoid": dedupe(d["foods_to_avoid"]),
        "recommended_food_type": d["recommended_food_type"],
        "meals_per_day": meals_from_routine(d["routine"], d["meals_per_day"]),
        "routine": d["routine"],
        "daily_food_g_min": d["daily_food_g_min"] if bird else None,
        "daily_food_g_max": d["daily_food_g_max"] if bird else None,
        "reviewed": False,
    }}


def dedupe(items: list[str]) -> list[str]:
    seen = set()
    return [i for i in items if not (i.lower() in seen or seen.add(i.lower()))]


def meals_from_routine(routine: dict, stated: dict) -> dict:
    """The LLM often contradicts itself (routine has 4 meals, meals_per_day says 2): trust the routine."""
    return {stage: sum(i["category"] == "meal" for i in items) or stated.get(stage) for stage, items in routine.items()}


def sanity(f: dict) -> list[str]:
    """Cheap checks that point the human reviewer at likely LLM mistakes."""
    out = []
    if f["daily_food_g_max"] and f["adult_weight_max_kg"]:
        share = f["daily_food_g_max"] / (f["adult_weight_max_kg"] * 1000)
        if not 0.05 <= share <= 0.35:
            out.append(f"bird food {f['daily_food_g_max']} g/day is {share:.0%} of body weight")
    for stage, items in f["routine"].items():
        meals = sum(i["category"] == "meal" for i in items)
        if meals != f["meals_per_day"].get(stage):
            out.append(f"{stage} routine has {meals} meals, meals_per_day says {f['meals_per_day'].get(stage)}")
    return out


def save(rows: list[dict], out: Path) -> None:
    # Fixed pks (sorted by label) make `loaddata breeds` safe to re-run.
    rows.sort(key=lambda r: r["fields"]["model_label"])
    for pk, r in enumerate(rows, 1):
        r["pk"] = pk
    out.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument("--labels", type=Path, default=settings.MODEL_META)
        parser.add_argument("--out", type=Path, default=Path(settings.BASE_DIR) / "fixtures" / "breeds.json")

    def handle(self, *args, labels, out, **opts):
        out.parent.mkdir(exist_ok=True)
        rows = json.loads(out.read_text(encoding="utf-8")) if out.exists() else []
        for r in rows:  # rows drafted before meals_from_routine existed
            f = r["fields"]
            f["meals_per_day"] = meals_from_routine(f["routine"], f["meals_per_day"])
            f["foods_to_avoid"] = dedupe(f["foods_to_avoid"])
            if f["name"][:1].islower():  # the LLM sometimes answers "cockatiel"
                f["name"] = f["name"].title()
        done = {r["fields"]["model_label"] for r in rows}
        todo = [l for l in read_labels(labels) if l not in done]
        for i, label in enumerate(todo, 1):
            try:
                row = to_fixture(label, ask(label))
                for warning in sanity(row["fields"]):
                    self.stdout.write(self.style.WARNING(f"REVIEW {label}: {warning}"))
                rows.append(row)
            except Exception as e:  # keep going; rerun picks up what failed
                self.stderr.write(f"{label}: {e}")
                continue
            save(rows, out)
            self.stdout.write(f"[{i}/{len(todo)}] {label}")
        save(rows, out)
        self.stdout.write(self.style.SUCCESS(f"{len(rows)} breeds in {out}. Spot-check them, then set reviewed."))
