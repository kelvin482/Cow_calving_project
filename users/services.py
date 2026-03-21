from django.db import transaction

from .models import Profile


@transaction.atomic
def get_or_create_profile(user):
    # Existing accounts may not have a profile yet, so create one lazily to
    # keep the new role system backward compatible with current users.
    profile, _ = Profile.objects.select_for_update().get_or_create(user=user)
    return profile


def get_post_login_url_for_user(user, fallback="/dashboard/profile/"):
    profile = get_or_create_profile(user)
    if profile.role:
        if profile.role.post_login_path:
            return profile.role.post_login_path
        if profile.role.default_path:
            return profile.role.default_path
    return fallback


def get_dashboard_url_for_user(user, fallback="/dashboard/profile/"):
    profile = get_or_create_profile(user)
    if profile.role and profile.role.default_path:
        return profile.role.default_path
    return fallback
