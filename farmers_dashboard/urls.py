from django.urls import path

from .views import dashboard_view

app_name = "farmers_dashboard"

urlpatterns = [
    path("", dashboard_view, name="dashboard"),
]
