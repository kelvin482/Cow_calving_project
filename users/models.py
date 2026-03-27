from django.conf import settings
from django.db import models


class Role(models.Model):
    # Store role metadata in the database so dashboard routing can grow beyond
    # the first two roles without hardcoding every future role in Python.
    slug = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    post_login_path = models.CharField(max_length=255, blank=True)
    dashboard_namespace = models.CharField(max_length=100, blank=True)
    default_path = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Profile(models.Model):
    LOCATION_SOURCE_MANUAL_PIN = "manual_pin"
    LOCATION_SOURCE_CURRENT = "current_location"

    LOCATION_SOURCE_CHOICES = [
        (LOCATION_SOURCE_MANUAL_PIN, "Pin on map"),
        (LOCATION_SOURCE_CURRENT, "Current location"),
    ]

    # Keep application-specific details here so the auth app can stay focused
    # on login, registration, reset, and verification flows.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="profiles",
    )
    farm_name = models.CharField(max_length=200, blank=True)
    phone_number = models.CharField(max_length=30, blank=True)
    farm_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    farm_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    farm_location_source = models.CharField(
        max_length=32,
        choices=LOCATION_SOURCE_CHOICES,
        blank=True,
        default="",
    )
    farm_location_updated_at = models.DateTimeField(null=True, blank=True)
    professional_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    is_profile_complete = models.BooleanField(default=False)

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        return f"Profile for {self.user.username}"

    @property
    def dashboard_slug(self):
        return self.role.slug if self.role else ""

    @property
    def has_farm_location(self):
        return self.farm_latitude is not None and self.farm_longitude is not None

    @property
    def farm_location_label(self):
        if self.farm_location_source == self.LOCATION_SOURCE_CURRENT:
            return "Current location"
        if self.farm_location_source == self.LOCATION_SOURCE_MANUAL_PIN:
            return "Pinned on map"
        return "Location source"

    def save(self, *args, **kwargs):
        # Admin-provisioned veterinary IDs should stay normalized so sign-in
        # remains case-insensitive and duplicate formatting does not slip in.
        if self.professional_id is not None:
            normalized_professional_id = self.professional_id.strip().upper()
            self.professional_id = normalized_professional_id or None
        super().save(*args, **kwargs)
