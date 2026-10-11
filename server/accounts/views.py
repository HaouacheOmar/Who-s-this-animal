from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from .models import User
from .tokens import reset_token, verification_token


class AuthThrottle(SimpleRateThrottle):
    scope = "auth"  # per-IP, rate in settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


def public(view):
    return permission_classes([AllowAny])(throttle_classes([AuthThrottle])(view))


def me_payload(user):
    return {"id": user.id, "email": user.email, "email_verified": user.email_verified}


def link(kind: str, user, token) -> str:
    return f"{settings.FRONTEND_URL}/{kind}/{urlsafe_base64_encode(force_bytes(user.pk))}/{token.make_token(user)}"


def send_verification(user):
    send_mail("Verify your email — Who's This Animal",
              f"Welcome! Confirm your email to start:\n\n{link('verify-email', user, verification_token)}\n\n"
              "The link expires in 24 hours.", None, [user.email])


def user_from_uid(uid):
    try:
        return User.objects.get(pk=urlsafe_base64_decode(uid).decode())
    except (User.DoesNotExist, ValueError, TypeError):
        return None


def find_user(email):
    return User.objects.filter(email__iexact=(email or "").strip()).first()


@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def csrf(request):
    return Response({"ok": True})


@api_view(["POST"])
@public
def register(request):
    email = (request.data.get("email") or "").strip().lower()
    password = request.data.get("password") or ""
    errors = {}
    try:
        validate_email(email)
    except ValidationError:
        errors["email"] = ["Enter a valid email address."]
    if not errors and find_user(email):
        errors["email"] = ["An account with this email already exists."]
    if password != request.data.get("password_confirm"):
        errors["password_confirm"] = ["Passwords don't match."]
    try:
        validate_password(password, User(email=email))
    except ValidationError as e:
        errors["password"] = list(e.messages)
    if errors:
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(email, password)
    try:
        send_verification(user)
    except OSError:
        pass  # PRD S1 5a: account exists, the page offers "Resend email"
    return Response(me_payload(user), status=status.HTTP_201_CREATED)


@api_view(["POST"])
@public
def verify_email(request):
    user = user_from_uid(request.data.get("uid", ""))
    if user and user.email_verified:
        return Response({"detail": "already_verified"})
    if not user or not verification_token.check_token(user, request.data.get("token", "")):
        return Response({"detail": "This link is invalid or expired."}, status=status.HTTP_400_BAD_REQUEST)
    user.email_verified = True
    user.save(update_fields=["email_verified"])
    return Response({"detail": "verified"})


@api_view(["POST"])
@public
def resend_verification(request):
    user = find_user(request.data.get("email"))
    if user and not user.email_verified:
        send_verification(user)
    return Response({"detail": "If an unverified account exists, we sent a new link."})


@api_view(["POST"])
@public
def login_view(request):
    user = authenticate(request, username=(request.data.get("email") or "").strip().lower(),
                        password=request.data.get("password") or "")
    if not user:
        return Response({"detail": "Email or password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)
    if not user.email_verified:
        return Response({"detail": "Please verify your email first.", "code": "email_not_verified"},
                        status=status.HTTP_403_FORBIDDEN)
    login(request, user)
    return Response(me_payload(user))


@api_view(["POST"])
def logout_view(request):
    logout(request)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
def me(request):
    return Response(me_payload(request.user))


@api_view(["POST"])
@public
def password_reset(request):
    user = find_user(request.data.get("email"))
    if user:
        send_mail("Reset your password — Who's This Animal",
                  f"Set a new password here:\n\n{link('reset-password', user, reset_token)}\n\n"
                  "If you didn't ask for this, ignore this email.", None, [user.email])
    return Response({"detail": "If an account exists, we sent a reset link."})


@api_view(["POST"])
@public
def password_reset_confirm(request):
    user = user_from_uid(request.data.get("uid", ""))
    if not user or not reset_token.check_token(user, request.data.get("token", "")):
        return Response({"detail": "This link is invalid or expired."}, status=status.HTTP_400_BAD_REQUEST)
    password = request.data.get("password") or ""
    if password != request.data.get("password_confirm"):
        return Response({"password_confirm": ["Passwords don't match."]}, status=status.HTTP_400_BAD_REQUEST)
    try:
        validate_password(password, user)
    except ValidationError as e:
        return Response({"password": list(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
    user.set_password(password)
    user.save(update_fields=["password"])
    return Response({"detail": "Password changed."})
