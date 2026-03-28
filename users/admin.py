from django.contrib import admin

from .models import Profile, Role


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "post_login_path",
        "dashboard_namespace",
        "default_path",
        "is_active",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "slug")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "role",
        "professional_id",
        "farm_name",
        "is_profile_complete",
    )
    list_filter = ("role", "is_profile_complete")
    search_fields = (
        "user__username",
        "user__email",
        "farm_name",
        "professional_id",
    )
