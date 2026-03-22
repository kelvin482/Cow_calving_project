from django.urls import path

from .views import (
    analytics_view,
    dashboard_view,
    diagnosis_view,
    farms_view,
    labs_view,
    patients_view,
    prescriptions_view,
    schedule_view,
    telehealth_view,
)

app_name = "veterinary_dashboard"

urlpatterns = [
    path("", dashboard_view, name="dashboard"),
    path("schedule/", schedule_view, name="schedule"),
    path("farms/", farms_view, name="farms"),
    path("patients/", patients_view, name="patients"),
    path("diagnosis/", diagnosis_view, name="diagnosis"),
    path("prescriptions/", prescriptions_view, name="prescriptions"),
    path("labs/", labs_view, name="labs"),
    path("telehealth/", telehealth_view, name="telehealth"),
    path("analytics/", analytics_view, name="analytics"),
]
