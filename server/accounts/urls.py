from django.urls import path

from . import views

urlpatterns = [
    path("csrf/", views.csrf),
    path("register/", views.register),
    path("verify-email/", views.verify_email),
    path("resend-verification/", views.resend_verification),
    path("login/", views.login_view),
    path("logout/", views.logout_view),
    path("me/", views.me),
    path("password-reset/", views.password_reset),
    path("password-reset/confirm/", views.password_reset_confirm),
]
