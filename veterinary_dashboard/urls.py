from django.urls import path

from .views import (
    analytics_view,
    dashboard_view,
    diagnosis_view,
    farm_map_view,
    labs_view,
    medical_records_view,
    messages_view,
    notifications_view,
    patients_view,
    prescriptions_view,
    schedule_view,
    telehealth_view,
)

app_name = "veterinary_dashboard"

urlpatterns = [
    path("", dashboard_view, name="dashboard"),
    path("farm-map/", farm_map_view, name="farm_map"),
    path("messages/", messages_view, name="messages"),
    path("messages/<int:thread_id>/", messages_view, name="messages_thread"),
    path("medical-records/", medical_records_view, name="medical_records"),
    path("notifications/", notifications_view, name="notifications"),
    path("schedule/", schedule_view, name="schedule"),
    path("patients/", patients_view, name="patients"),
    path("diagnosis/", diagnosis_view, name="diagnosis"),
    path("prescriptions/", prescriptions_view, name="prescriptions"),
    path("labs/", labs_view, name="labs"),
    path("telehealth/", telehealth_view, name="telehealth"),
    path("analytics/", analytics_view, name="analytics"),
]
