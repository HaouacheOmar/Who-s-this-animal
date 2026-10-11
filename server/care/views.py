from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from pets.models import Pet
from scans.models import Scan

from .llm import LLMUnavailable, personal_notes
from .models import Breed
from .sheet import care_sheet


@api_view(["GET"])
def breeds(request):
    qs = Breed.objects.select_related("species").order_by("name")
    if q := request.query_params.get("search"):
        qs = qs.filter(name__icontains=q)
    return Response([{"id": b.id, "name": b.name, "species": b.species.code} for b in qs[:30]])


@api_view(["GET"])
def care_text(request):
    """Personal notes for ?scan=<id> (breed average) or ?pet=<id> (personalised). 503 when Ollama is down."""
    if pet_id := request.query_params.get("pet"):
        pet = get_object_or_404(Pet.objects.select_related("breed__species"), pk=pet_id, owner=request.user)
        breed = pet.breed
    else:
        scan = get_object_or_404(Scan.objects.select_related("breed__species"), pk=request.query_params.get("scan"),
                                 owner=request.user)
        pet, breed = None, scan.breed
    if not breed:
        return Response({"detail": "No breed to describe."}, status=404)
    try:
        return Response({"text": personal_notes(breed, care_sheet(breed, pet), pet)})
    except LLMUnavailable:
        return Response({"detail": "Personal notes are unavailable right now."}, status=503)
