from django.urls import path

from .views import (
    alerts_view,
    cow_register_view,
    cow_tracking_view,
    dashboard_view,
    herd_view,
    location_view,
    messages_view,
    notifications_view,
    reports_view,
    search_view,
    service_finder_view,
)

app_name = "farmers_dashboard"

urlpatterns = [
    path("", dashboard_view, name="dashboard"),
    path("search/", search_view, name="search"),
    path("herd/register/", cow_register_view, name="cow_register"),
    path("herd/<int:cow_id>/tracking/", cow_tracking_view, name="cow_tracking"),
    path("herd/", herd_view, name="herd"),
    path("alerts/", alerts_view, name="alerts"),
    path("location/", location_view, name="location"),
    path("messages/", messages_view, name="messages"),
    path("messages/<int:thread_id>/", messages_view, name="messages_thread"),
    path("notifications/", notifications_view, name="notifications"),
    path("reports/", reports_view, name="reports"),
    path("services/", service_finder_view, name="service_finder"),
]
