from django.shortcuts import get_object_or_404
from PIL import Image
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from care.models import Breed
from care.sheet import care_sheet
from pets.models import Pet

from . import classifier
from .models import Scan

MAX_UPLOAD = 10 * 2**20
# Extension comes from the detected format, never the client filename: a JPEG named evil.html
# would otherwise be served from /media/ as HTML (stored XSS).
EXTENSIONS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


class ScanSerializer(serializers.ModelSerializer):
    breed_name = serializers.CharField(source="breed.name", read_only=True, default=None)
    pet_name = serializers.CharField(source="pet.name", read_only=True, default=None)

    class Meta:
        model = Scan
        fields = ["id", "image", "breed", "breed_name", "confidence", "top_k", "is_possible_mix", "reject_reason",
                  "model_version", "pet", "pet_name", "created_at"]


def with_care(scan: Scan) -> dict:
    data = ScanSerializer(scan).data
    data["care"] = care_sheet(scan.breed) if scan.breed else None
    return data


class HistoryPage(PageNumberPagination):
    page_size = 20


class ScanViewSet(mixins.ListModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    serializer_class = ScanSerializer
    pagination_class = HistoryPage

    def get_queryset(self):
        return (Scan.objects.filter(owner=self.request.user).select_related("breed__species", "pet")
                .order_by("-created_at"))

    def retrieve(self, request, pk=None):
        return Response(with_care(self.get_object()))

    def create(self, request):
        upload = request.FILES.get("image")
        if not upload or upload.size > MAX_UPLOAD:
            return Response({"detail": "Please upload a JPEG, PNG or WEBP image under 10 MB."}, status=400)
        try:
            with Image.open(upload) as im:
                fmt = im.format
        except Exception:
            fmt = None
        if fmt not in EXTENSIONS:
            return Response({"detail": "Please upload a JPEG, PNG or WEBP image under 10 MB."}, status=400)

        upload.seek(0)
        try:
            reply = classifier.classify(upload.read())
        except classifier.ModelUnavailable:
            return Response({"detail": "Identification service unavailable, try again."}, status=503)

        scan = Scan(owner=request.user, model_version=reply.model_version or None,
                    top_k=[{"label": p.label, "confidence": round(p.confidence, 4)} for p in reply.predictions])
        if reply.recognized:
            # check_labels guarantees every model label has a breed row
            scan.breed = Breed.objects.select_related("species").get(model_label=reply.predictions[0].label)
            scan.confidence = reply.predictions[0].confidence
            scan.is_possible_mix = reply.possible_mix
            labels = [p["label"] for p in scan.top_k]
            names = dict(Breed.objects.filter(model_label__in=labels).values_list("model_label", "name"))
            for p in scan.top_k:
                p["name"] = names.get(p["label"])
        else:
            scan.reject_reason = reply.reject_reason
            scan.confidence = reply.predictions[0].confidence if reply.predictions else None
        upload.seek(0)
        scan.image.save(f"upload{EXTENSIONS[fmt]}", upload, save=False)
        scan.save()
        return Response(with_care(scan), status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def attach(self, request, pk=None):
        scan = self.get_object()
        pet = get_object_or_404(Pet, pk=request.data.get("pet_id"), owner=request.user)
        scan.pet = pet
        scan.save(update_fields=["pet"])
        return Response({**with_care(scan), "breed_differs": bool(scan.breed_id and scan.breed_id != pet.breed_id)})
