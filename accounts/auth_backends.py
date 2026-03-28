from django.contrib.auth import get_user_model
from django.db.models import Q

from users.models import Profile


class EmailBackend:
    """Authenticate non-veterinary users with email and password."""

    def authenticate(self, request, email=None, password=None, **kwargs):
        normalized_email = (email or "").strip()
        if not normalized_email or not password:
            return None

        UserModel = get_user_model()
        user = UserModel._default_manager.filter(email__iexact=normalized_email).first()
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def get_user(self, user_id):
        UserModel = get_user_model()
        try:
            user = UserModel._default_manager.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
        return user if self.user_can_authenticate(user) else None

    def user_can_authenticate(self, user):
        is_active = getattr(user, "is_active", None)
        return is_active or is_active is None


class ProfessionalIDBackend:
    """Authenticate veterinary users with the professional ID assigned by admin."""

    def authenticate(self, request, professional_id=None, password=None, **kwargs):
        normalized_professional_id = (professional_id or "").strip().upper()
        if not normalized_professional_id or not password:
            return None

        profile = (
            Profile.objects.select_related("user", "role")
            .filter(
                professional_id=normalized_professional_id
            )
            .filter(Q(role__slug="veterinary") | Q(user__is_superuser=True))
            .first()
        )
        if not profile:
            return None

        user = profile.user
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def get_user(self, user_id):
        UserModel = get_user_model()
        try:
            user = UserModel._default_manager.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
        return user if self.user_can_authenticate(user) else None

    def user_can_authenticate(self, user):
        is_active = getattr(user, "is_active", None)
        return is_active or is_active is None
