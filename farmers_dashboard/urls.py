from django.urls import path

from .views import alerts_view, dashboard_view, herd_view, reports_view

app_name = "farmers_dashboard"

urlpatterns = [
    path("", dashboard_view, name="dashboard"),
    path("herd/", herd_view, name="herd"),
    path("alerts/", alerts_view, name="alerts"),
    path("reports/", reports_view, name="reports"),
]
