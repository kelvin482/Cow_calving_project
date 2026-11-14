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
        "dashboard_shell_template": "users/dashboard_shell.html",
        **extra,
    }


def _build_profile_page_context(
    request,
    profile,
    *,
    page_title,
    page_eyebrow,
    page_heading,
    page_intro,
    **extra,
):
    if profile.dashboard_slug == "farmer":
        # Reuse the farmer shell context so these account pages share its navigation.
        from farmers_dashboard.views import _build_farmer_dashboard_context

        return _build_farmer_dashboard_context(
            request,
            page_title=page_title,
            page_eyebrow=page_eyebrow,
            page_heading=page_heading,
            page_intro=page_intro,
            header_primary_action={
                "label": "Back to dashboard",
                "url": get_dashboard_url_for_user(request.user, profile=profile),
            },
            extra_context={
                "dashboard_shell_template": "farmers_dashboard/base_dashboard.html",
                **extra,
            },
        )

    return _build_dashboard_page_context(
        request,
        profile,
        dashboard_shell_template="users/dashboard_shell.html",
        page_title=page_title,
        **extra,
    )


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
        _build_profile_page_context(
            request,
            profile,
            page_title="My Profile | CowCalving",
            page_eyebrow="Farm profile",
            page_heading="Profile details",
            page_intro="Review your account and farm information.",
        ),
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
        _build_profile_page_context(
            request,
            profile,
            page_title="Update Farm Profile | CowCalving",
            page_eyebrow="Farm profile",
            page_heading="Update farm profile",
            page_intro="Keep your account and farm contact details current.",
            form=form,
        ),
    )
