from django.urls import path

from .views import about_view, checklist_view, guide_view, home_view

app_name = "Core_Web"

urlpatterns = [
    path("", home_view, name="home"),
    path("guide/", guide_view, name="guide"),
    path("checklist/", checklist_view, name="checklist"),
    path("about/", about_view, name="about"),
]
