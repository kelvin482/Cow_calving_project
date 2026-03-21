from allauth.account.signals import user_signed_up
from django.dispatch import receiver

from users.models import Role
from users.services import get_or_create_profile


@receiver(user_signed_up)
def assign_farmer_role_to_self_service_signups(request, user, **kwargs):
    # Public self-service account creation is reserved for farmers, including
    # social sign-ups that may bypass the local registration form.
    profile = get_or_create_profile(user)
    if profile.role_id:
        return

    farmer_role = Role.objects.filter(slug="farmer", is_active=True).first()
    if not farmer_role:
        return

    profile.role = farmer_role
    profile.is_profile_complete = all(
        [
            user.first_name.strip(),
            user.last_name.strip(),
            user.email.strip(),
        ]
    )
    profile.save(update_fields=["role", "is_profile_complete"])
