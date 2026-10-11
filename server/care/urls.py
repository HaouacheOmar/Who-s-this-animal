from django.urls import path

from . import views

urlpatterns = [
    path("breeds/", views.breeds),
    path("care-text/", views.care_text),
]
