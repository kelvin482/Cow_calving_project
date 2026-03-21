from django.conf import settings
from django.shortcuts import render

from users.services import get_dashboard_url_for_user, get_or_create_profile


def home_view(request):
    # Keep one public home page for everyone, then add small role-aware hints
    # for signed-in users so navigation stays obvious without extra training.
    dashboard_url = ""
    dashboard_label = ""
    profile_url = "/dashboard/profile/"

    if request.user.is_authenticated:
        profile = get_or_create_profile(request.user)
        dashboard_url = get_dashboard_url_for_user(
            request.user,
            fallback=profile_url,
        )
        dashboard_label = (
            f"Open {profile.role.name} Dashboard"
            if profile.role
            else "Complete Your Profile"
        )

    return render(
        request,
        "Core_Web/home.html",
        {
            "authenticated_default_url": settings.AUTHENTICATED_DEFAULT_URL,
            "dashboard_url": dashboard_url,
            "dashboard_label": dashboard_label,
        },
    )
