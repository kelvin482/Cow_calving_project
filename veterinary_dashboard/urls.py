from django.urls import path

from .views import dashboard_view

app_name = "veterinary_dashboard"

urlpatterns = [
    path("", dashboard_view, name="dashboard"),
]
