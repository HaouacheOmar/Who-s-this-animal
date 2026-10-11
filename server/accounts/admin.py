from django.contrib import admin

from .models import User

admin.site.register(User, list_display=["email", "email_verified", "is_staff", "date_joined"], search_fields=["email"])
