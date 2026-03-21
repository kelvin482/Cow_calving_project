from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from users.permissions import role_required
from users.services import get_dashboard_url_for_user, get_or_create_profile


@login_required
@role_required("farmer")
def dashboard_view(request):
    profile = get_or_create_profile(request.user)
    return render(
        request,
        "farmers_dashboard/dashboard.html",
        {
            "dashboard_home_url": get_dashboard_url_for_user(
                request.user,
                fallback="/dashboard/profile/",
            ),
            "profile": profile,
        },
    )
