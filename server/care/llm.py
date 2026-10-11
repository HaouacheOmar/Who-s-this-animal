"""Personal notes from local Ollama, cached in care_texts (IMPLEMENTATION.md §7.3)."""
import hashlib
import json
import urllib.error
import urllib.request

from django.conf import settings

from .models import CareText
from .sheet import age_months

PROMPT_VERSION = 2  # bump when the prompt or the facts it receives change: invalidates cached notes


class LLMUnavailable(Exception):
    pass


def profile(pet) -> dict:
    if not pet:
        return {"pet": None}
    return {"name": pet.name, "age_months": age_months(pet.birth_date), "weight_kg": round(float(pet.weight_kg) * 2) / 2,
            "sex": pet.sex, "neutered": pet.neutered, "activity": pet.activity_level}


def profile_hash(breed_id: int, prof: dict) -> str:
    raw = json.dumps({"breed": breed_id, "v": PROMPT_VERSION, **prof}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def build_prompt(sheet: dict, prof: dict) -> str:
    b, feeding = sheet["breed"], sheet["feeding"]
    who = (f"The pet is {prof['name']}, a {prof['age_months']}-month-old {prof['sex']} {b['name']}, "
           f"{prof['weight_kg']} kg, {'neutered' if prof['neutered'] else 'not neutered'}, {prof['activity']} activity."
           if prof.get("name") else f"The owner has just identified their pet as a {b['name']}; no profile yet.")
    return (
        "You are a friendly pet-care guide for first-time owners in Algeria.\n"
        f"{who}\n"
        f"Curated facts (do not change any numbers): {json.dumps({'breed': b, 'life_stage': sheet['life_stage'], 'feeding': feeding, 'foods_to_avoid': sheet['foods_to_avoid']}, default=str)}\n"
        "Write 3 short, warm paragraphs in plain English: what to expect from this pet, how to feed it day to day, "
        "and one or two tips for the first weeks together. Use the pet's name if given. "
        "Do not give medical diagnoses. Do not invent numbers. No headings, no lists, no markdown."
    )


def personal_notes(breed, sheet: dict, pet=None) -> str:
    prof = profile(pet)
    key = profile_hash(breed.id, prof)
    cached = CareText.objects.filter(breed=breed, profile_hash=key).first()
    if cached:
        return cached.content

    body = json.dumps({"model": settings.OLLAMA_MODEL, "prompt": build_prompt(sheet, prof),
                       "stream": False, "think": False}).encode()
    req = urllib.request.Request(f"{settings.OLLAMA_URL}/api/generate", body, {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            text = json.load(r)["response"].strip()
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as e:
        raise LLMUnavailable(str(e)) from e

    CareText.objects.get_or_create(breed=breed, profile_hash=key,
                                   defaults={"content": text, "llm_model": settings.OLLAMA_MODEL})
    return text
