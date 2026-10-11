from django.test import SimpleTestCase

from care.feeding import grams_per_day, life_stage, mer, rer


class FeedingTests(SimpleTestCase):
    def test_known_dog(self):
        # 10 kg neutered adult dog: RER ≈ 393.6, MER ≈ 629.8 (IMPLEMENTATION.md §7.2)
        self.assertAlmostEqual(rer(10), 393.6, places=1)
        self.assertAlmostEqual(mer("dog", 10, "adult", 36, neutered=True), 629.8, places=1)
        self.assertAlmostEqual(grams_per_day(629.8, 380), 165.7, places=1)

    def test_life_stages(self):
        self.assertEqual(life_stage("dog", 14, adult_age_months=18, size_class="large"), "young")
        self.assertEqual(life_stage("dog", 66, size_class="giant"), "senior")
        self.assertEqual(life_stage("dog", 66, size_class="small"), "adult")
        self.assertEqual(life_stage("cat", 140), "senior")
        self.assertEqual(life_stage("bird", 2), "adult")

    def test_puppy_and_activity(self):
        self.assertAlmostEqual(mer("dog", 5, "young", 3, False), rer(5) * 3.0)
        self.assertAlmostEqual(mer("cat", 4, "adult", 30, True, "high"), rer(4) * 1.2 * 1.2)
