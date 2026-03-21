from datetime import timedelta
from random import SystemRandom

from django.conf import settings
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .forms import (
    CowCalvingLoginForm,
    CowCalvingRegisterForm,
    PasswordResetCodeConfirmForm,
    PasswordResetCodeRequestForm,
)
from allauth.account import app_settings as allauth_settings
from allauth.account.utils import setup_user_email
from django.urls import reverse

PASSWORD_RESET_SESSION_KEY = "password_reset_code_state"
PASSWORD_RESET_CODE_LENGTH = 6
PASSWORD_RESET_CODE_TTL_SECONDS = 10 * 60


def _hash_reset_code(email, code):
    # Store only a derived hash in session so the raw reset code is not persisted.
    return salted_hmac(
        "accounts.password_reset_code",
        f"{email.lower()}:{code}",
    ).hexdigest()


def _generate_reset_code():
    # A fixed-width numeric code keeps the reset UX simple for beginners.
    maximum = 10**PASSWORD_RESET_CODE_LENGTH - 1
    return f"{SystemRandom().randint(0, maximum):0{PASSWORD_RESET_CODE_LENGTH}d}"


def _store_reset_state(request, user, code):
    # The reset flow is session-bound on purpose so users do not need a long URL token.
    expires_at = timezone.now() + timedelta(seconds=PASSWORD_RESET_CODE_TTL_SECONDS)
    request.session[PASSWORD_RESET_SESSION_KEY] = {
        "user_id": user.pk,
        "email": user.email,
        "code_hash": _hash_reset_code(user.email, code),
        "expires_at": expires_at.isoformat(),
    }
    request.session.modified = True


def _clear_reset_state(request):
    request.session.pop(PASSWORD_RESET_SESSION_KEY, None)
    request.session.modified = True


def _get_reset_state(request):
    # Expired or malformed session state is cleared eagerly to avoid stale reset attempts.
    state = request.session.get(PASSWORD_RESET_SESSION_KEY)
    if not state:
        return None

    expires_raw = state.get("expires_at")
    try:
        expires_at = timezone.datetime.fromisoformat(expires_raw)
    except (TypeError, ValueError):
        _clear_reset_state(request)
        return None

    if timezone.is_naive(expires_at):
        expires_at = timezone.make_aware(expires_at, timezone.get_current_timezone())

    if timezone.now() >= expires_at:
        _clear_reset_state(request)
        return None

    state["expires_at"] = expires_at
    return state


def _send_password_reset_code(user, code):
    # Keep the email plain and short so the code is easy to spot on mobile devices.
    send_mail(
        subject="Your CowCalving password reset code",
        message=(
            "Use this code to reset your password:\n\n"
            f"{code}\n\n"
            "The code expires in 10 minutes."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


@never_cache
def csrf_failure_view(request, reason="", template_name="accounts/csrf_failure.html"):
    # A stale or reused form token should send the user back gently instead of showing Django's raw debug page.
    return render(
        request,
        template_name,
        {"reason": reason},
        status=403,
    )


@never_cache
@require_http_methods(["GET", "POST"])
def login_view(request):
    # Visiting login/signup is treated as a fresh auth start, so we clear any
    # old session instead of silently reusing it.
    if request.user.is_authenticated:
        auth_logout(request)
        messages.info(request, "Please sign in again to continue.")

    form = CowCalvingLoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        auth_login(request, form.get_user())
        return redirect(settings.LOGIN_REDIRECT_URL)

    return render(request, "accounts/login.html", {"form": form})


@never_cache
@require_http_methods(["GET", "POST"])
def register_view(request):
    # Match the login page behavior so returning users always start from a
    # clean session before creating or switching accounts.
    if request.user.is_authenticated:
        auth_logout(request)
        messages.info(request, "Your previous session was closed. Create or sign in again.")

    # UserCreationForm keeps password rules aligned with Django validators.
    form = CowCalvingRegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        primary_email = setup_user_email(request, user, [])
        if primary_email:
            primary_email.send_confirmation(request, signup=True)
        if (
            allauth_settings.EMAIL_VERIFICATION
            == allauth_settings.EmailVerificationMethod.MANDATORY
        ):
            # Mandatory verification should land on the styled confirmation page
            # until the user verifies and signs in for role-based routing.
            messages.success(
                request,
                "Check your email to verify your account before signing in to your dashboard.",
            )
            return redirect(reverse("account_email_verification_sent"))

        # New users do not carry an auth backend on the model instance yet, so
        # select the primary configured backend explicitly before login().
        auth_login(request, user, backend=settings.AUTHENTICATION_BACKENDS[0])
        return redirect(settings.LOGIN_REDIRECT_URL)

    return render(request, "accounts/register.html", {"form": form})


@never_cache
@require_http_methods(["GET", "POST"])
def password_reset_request_view(request):
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    initial = {}
    state = _get_reset_state(request)
    if state:
        initial["email"] = state.get("email", "")

    form = PasswordResetCodeRequestForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].strip()
        # Use the email as the account identifier so the reset flow stays easy
        # to understand even for users who do not remember their username.
        user = User.objects.filter(email__iexact=email, is_active=True).first()

        if not user:
            _clear_reset_state(request)
            form.add_error("email", "We could not find an active account with that email.")
            return render(request, "accounts/password_reset_request.html", {"form": form})

        # Any active account with a known email can receive a reset code and set
        # a local password, even if the account was originally created by social login.
        code = _generate_reset_code()
        _store_reset_state(request, user, code)
        try:
            _send_password_reset_code(user, code)
        except Exception:
            _clear_reset_state(request)
            messages.error(
                request,
                "We could not send the reset code right now. Please try again in a moment.",
            )
            return render(
                request,
                "accounts/password_reset_request.html",
                {"form": form},
            )

        messages.success(
            request,
            "We sent a 6-digit code to your email. Enter it on the next page.",
        )
        return redirect("accounts:password_reset_verify")

    return render(request, "accounts/password_reset_request.html", {"form": form})


@never_cache
@require_http_methods(["GET", "POST"])
def password_reset_verify_view(request):
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    state = _get_reset_state(request)
    if not state:
        # The verify step only works after the request step creates a fresh
        # session-bound reset state.
        messages.error(request, "Request a new reset code to continue.")
        return redirect("accounts:password_reset_request")

    user = User.objects.filter(
        pk=state.get("user_id"),
        email__iexact=state.get("email", ""),
        is_active=True,
    ).first()
    if not user:
        _clear_reset_state(request)
        messages.error(request, "Request a new reset code to continue.")
        return redirect("accounts:password_reset_request")

    form = PasswordResetCodeConfirmForm(user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        code = form.cleaned_data["code"]
        expected_hash = state.get("code_hash", "")
        if _hash_reset_code(user.email, code) != expected_hash:
            form.add_error("code", "That reset code is not valid.")
        else:
            # SetPasswordForm applies Django's password validators before save().
            form.save()
            _clear_reset_state(request)
            messages.success(request, "Your password has been reset. Sign in below.")
            return redirect("accounts:login")

    return render(
        request,
        "accounts/password_reset_verify.html",
        {
            "form": form,
            "reset_email": user.email,
        },
    )


@require_http_methods(["GET"])
def password_reset_done_redirect_view(request):
    # Keep old reset URLs pointed at the active email-code flow to avoid mixed UX.
    if _get_reset_state(request):
        return redirect("accounts:password_reset_verify")
    return redirect("accounts:password_reset_request")


@require_http_methods(["POST"])
def logout_view(request):
    auth_logout(request)
    return redirect(settings.LOGOUT_REDIRECT_URL)

# Create your views here.
