import uuid
from datetime import date
from pathlib import Path

from django.core.files.base import ContentFile
from rest_framework import serializers, viewsets

from care.models import Breed
from care.sheet import care_sheet
from scans.models import Scan

from .models import Pet


class PetSerializer(serializers.ModelSerializer):
    breed = serializers.PrimaryKeyRelatedField(queryset=Breed.objects.all(), allow_null=True, required=False)
    breed_name = serializers.CharField(source="breed.name", read_only=True, default=None)
    from_scan = serializers.IntegerField(write_only=True, required=False)
    weight_warning = serializers.SerializerMethodField()

    class Meta:
        model = Pet
        fields = ["id", "name", "breed", "breed_name", "birth_date", "sex", "neutered", "weight_kg", "activity_level",
                  "photo", "created_at", "updated_at", "from_scan", "weight_warning"]
        read_only_fields = ["photo", "created_at", "updated_at"]

    def validate_birth_date(self, value):
        if value > date.today():
            raise serializers.ValidationError("Birth date can't be in the future.")
        return value

    def validate_weight_kg(self, value):
        if value <= 0:
            raise serializers.ValidationError("Weight must be more than 0 kg.")
        return value

    def get_weight_warning(self, pet):
        # PRD S9 2b: warn, don't block, when > 50% above the breed's adult max.
        b = pet.breed
        if b and b.adult_weight_max_kg and pet.weight_kg > b.adult_weight_max_kg * 3 / 2:
            return f"This is heavier than usual for a {b.name}. Double-check the weight or ask a vet."
        return None

    def create(self, data):
        scan_id = data.pop("from_scan", None)
        pet = super().create(data)
        if scan_id:
            scan = Scan.objects.get(pk=scan_id, owner=pet.owner)
            scan.pet = pet
            scan.save(update_fields=["pet"])
            with scan.image.open("rb") as f:  # own copy: deleting the scan must not remove the pet's photo
                pet.photo.save(f"{uuid.uuid4().hex}{Path(scan.image.name).suffix}", ContentFile(f.read()))
        return pet

    def validate_from_scan(self, value):
        if not Scan.objects.filter(pk=value, owner=self.context["request"].user).exists():
            raise serializers.ValidationError("Scan not found.")
        return value


class PetViewSet(viewsets.ModelViewSet):
    serializer_class = PetSerializer

    def get_queryset(self):
        return Pet.objects.filter(owner=self.request.user).select_related("breed__species").order_by("name")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        pet = self.get_object()
        response.data["care"] = care_sheet(pet.breed, pet) if pet.breed else None
        response.data["scans"] = list(pet.scans.order_by("-created_at").values("id", "created_at", "confidence"))
        return response

    def perform_destroy(self, pet):
        pet.photo.delete(save=False)
        pet.delete()
