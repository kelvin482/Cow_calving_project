from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ProfileUpdateForm
from .services import get_dashboard_url_for_user
from .services import get_post_login_url_for_user
from .services import get_profile


def _build_dashboard_page_context(request, profile, **extra):
    return {
        "dashboard_home_url": get_dashboard_url_for_user(
            request.user,
            fallback=settings.AUTHENTICATED_DEFAULT_URL,
            profile=profile,
        ),
        "profile": profile,
        **extra,
    }


@login_required
def dashboard_redirect_view(request):
    # Keep one shared redirect endpoint so login, social auth, and future
    # onboarding can route users without duplicating role logic.
    profile = get_profile(request.user)
    return redirect(
        get_post_login_url_for_user(
            request.user,
            fallback=settings.AUTHENTICATED_DEFAULT_URL,
            profile=profile,
        )
    )


@login_required
def profile_detail_view(request):
    profile = get_profile(request.user)
    return render(
        request,
        "users/profile_detail.html",
        _build_dashboard_page_context(request, profile),
    )


@login_required
def profile_edit_view(request):
    profile = get_profile(request.user)
    form = ProfileUpdateForm(
        request.POST or None,
        user=request.user,
        profile=profile,
    )

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your profile details have been updated.")
        return redirect("users:profile")

    return render(
        request,
        "users/profile_form.html",
        _build_dashboard_page_context(
            request,
            profile,
            form=form,
        ),
    )
