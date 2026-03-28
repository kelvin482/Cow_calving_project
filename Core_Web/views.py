from django.conf import settings
from django.shortcuts import render

from users.services import get_dashboard_url_for_user, get_profile


def _build_site_context(request, page_key):
    # Keep the public website pages on one shared context so navigation and
    # role-aware actions stay consistent across the website.
    dashboard_url = ""
    dashboard_label = ""
    profile_url = "/dashboard/profile/"
    role_slug = ""

    if request.user.is_authenticated:
        profile = get_profile(request.user)
        dashboard_url = get_dashboard_url_for_user(
            request.user,
            fallback=profile_url,
            profile=profile,
        )
        role_slug = profile.role.slug if profile.role else ""
        dashboard_label = (
            f"{profile.role.name} Dashboard"
            if profile.role
            else "Complete Your Profile"
        )

    return {
        "authenticated_default_url": settings.AUTHENTICATED_DEFAULT_URL,
        "dashboard_url": dashboard_url,
        "dashboard_label": dashboard_label,
        "profile_url": profile_url,
        "page_key": page_key,
        "role_slug": role_slug,
    }


def _render_site_page(request, template_name, page_key):
    return render(
        request,
        template_name,
        _build_site_context(request, page_key=page_key),
    )


def home_view(request):
    return _render_site_page(request, "Core_Web/home.html", page_key="home")


def guide_view(request):
    return _render_site_page(request, "Core_Web/guide.html", page_key="guide")


def checklist_view(request):
    return _render_site_page(request, "Core_Web/checklist.html", page_key="checklist")
