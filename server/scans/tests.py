"""End-to-end API flow (PRD S1-S3, S5, S7, S9, S14) with the model service and Ollama mocked."""
import io
import re
import shutil
import tempfile
from unittest import mock

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from care.models import Breed, FoodProduct, Species
from scans import classifier_pb2 as pb

MEDIA = tempfile.mkdtemp()


def jpeg():
    buf = io.BytesIO()
    Image.new("RGB", (300, 300), "orange").save(buf, "JPEG")
    buf.seek(0)
    buf.name = "pet.jpg"
    return buf


def reply(recognized=True, conf=0.94):
    return pb.ClassifyReply(recognized=recognized, model_version="test-v1",
                            reject_reason="" if recognized else "low_confidence",
                            predictions=[pb.Prediction(label="dog_beagle", confidence=conf),
                                         pb.Prediction(label="dog_basset", confidence=0.03)])


@override_settings(MEDIA_ROOT=MEDIA, OLLAMA_URL="http://127.0.0.1:9")  # port 9: nothing listens -> LLM down
class ApiFlowTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        cache.clear()  # auth throttle counts live in the cache
        dog = Species.objects.get(code="dog")
        Breed.objects.create(species=dog, model_label="dog_beagle", name="Beagle", size_class="small",
                             adult_weight_min_kg=9, adult_weight_max_kg=11, meals_per_day={"young": 3, "adult": 2},
                             routine={"adult": [{"time": "07:00", "activity": "Walk", "duration_min": 30,
                                                 "category": "exercise"}]})
        FoodProduct.objects.create(species=dog, brand="Brit", name="Adult Small", food_type="dry", life_stage="adult",
                                   kcal_per_100g=380)
        self.c = APIClient()

    def signup_and_login(self, email="owner@example.com", password="pawsome-Pass-42"):
        r = self.c.post("/api/auth/register/", {"email": email, "password": password, "password_confirm": password})
        self.assertEqual(r.status_code, 201, r.data)
        r = self.c.post("/api/auth/login/", {"email": email, "password": password})
        self.assertEqual(r.data["code"], "email_not_verified")  # S3 2b

        uid, token = re.search(r"/verify-email/([^/]+)/(\S+)", mail.outbox[-1].body).groups()
        self.assertEqual(self.c.post("/api/auth/verify-email/", {"uid": uid, "token": token}).data["detail"], "verified")
        self.assertEqual(self.c.post("/api/auth/verify-email/", {"uid": uid, "token": token}).data["detail"],
                         "already_verified")
        self.assertEqual(self.c.post("/api/auth/login/", {"email": email, "password": password}).status_code, 200)

    def test_scan_to_pet_flow(self):
        self.signup_and_login()
        with mock.patch("scans.classifier.classify", return_value=reply()):
            r = self.c.post("/api/scans/", {"image": jpeg()}, format="multipart")
        self.assertEqual(r.status_code, 201, r.data)
        scan = r.data
        self.assertEqual(scan["breed_name"], "Beagle")
        self.assertEqual(scan["top_k"][0]["name"], "Beagle")
        # breed average: neutered adult 9-11 kg -> MER range, grams for the 380 kcal food
        self.assertEqual(scan["care"]["feeding"]["kcal_per_day"], [582, 676])
        self.assertEqual(scan["care"]["feeding"]["products"][0]["grams_per_day"], [153, 178])

        self.assertEqual(self.c.get(f"/api/care-text/?scan={scan['id']}").status_code, 503)  # S14

        r = self.c.post("/api/pets/", {"name": "Rex", "breed": scan["breed"], "birth_date": "2022-01-01",
                                       "sex": "male", "neutered": True, "weight_kg": "10", "from_scan": scan["id"]})
        self.assertEqual(r.status_code, 201, r.data)
        pet = self.c.get(f"/api/pets/{r.data['id']}/").data
        self.assertTrue(pet["photo"])
        self.assertEqual(pet["care"]["feeding"]["kcal_per_day"], [630])  # same as test_feeding's known case
        self.assertEqual([s["id"] for s in pet["scans"]], [scan["id"]])

    def test_rejections_and_scoping(self):
        self.signup_and_login()
        with mock.patch("scans.classifier.classify", return_value=reply(recognized=False, conf=0.2)):
            r = self.c.post("/api/scans/", {"image": jpeg()}, format="multipart")
        self.assertEqual((r.data["reject_reason"], r.data["breed"], r.data["care"]), ("low_confidence", None, None))

        evil = jpeg()  # valid JPEG bytes, hostile name: must be stored as .jpg, not served as HTML
        evil.name = "evil.html"
        with mock.patch("scans.classifier.classify", return_value=reply()):
            r2 = self.c.post("/api/scans/", {"image": evil}, format="multipart")
        self.assertTrue(r2.data["image"].endswith(".jpg"), r2.data["image"])

        bad = io.BytesIO(b"GIF89a not really")
        bad.name = "x.gif"
        self.assertEqual(self.c.post("/api/scans/", {"image": bad}, format="multipart").status_code, 400)

        other = APIClient()
        self.c = other
        self.signup_and_login("someone@example.com")
        self.assertEqual(other.get(f"/api/scans/{r.data['id']}/").status_code, 404)
        self.assertEqual(other.get("/api/scans/").data["count"], 0)
