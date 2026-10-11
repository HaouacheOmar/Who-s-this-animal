from django.contrib import admin

from .models import Breed, CareText, FoodProduct, Species

admin.site.register(Species)
admin.site.register(Breed, list_display=["name", "species", "model_label", "reviewed"], list_filter=["species", "reviewed"],
                    search_fields=["name", "model_label"])
admin.site.register(FoodProduct, list_display=["brand", "name", "species", "life_stage", "kcal_per_100g"])
admin.site.register(CareText, list_display=["breed", "llm_model", "created_at"])
