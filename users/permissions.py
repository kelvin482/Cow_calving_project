from functools import wraps

from django.conf import settings
from django.shortcuts import redirect

from .services import get_dashboard_url_for_user, get_or_create_profile


def role_required(expected_slug):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            profile = get_or_create_profile(request.user)
            if profile.role and profile.role.slug == expected_slug:
                return view_func(request, *args, **kwargs)

            # Redirect users to their own dashboard if they hit the wrong one
            # so role protection feels intentional instead of abrupt.
            return redirect(
                get_dashboard_url_for_user(
                    request.user,
                    fallback=settings.AUTHENTICATED_DEFAULT_URL,
                )
            )

        return wrapped

    return decorator
