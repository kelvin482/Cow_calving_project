from django.urls import path

from .views import dashboard_redirect_view, profile_detail_view, profile_edit_view

app_name = "users"

urlpatterns = [
    path("", dashboard_redirect_view, name="dashboard"),
    path("profile/", profile_detail_view, name="profile"),
    path("profile/edit/", profile_edit_view, name="profile_edit"),
]
