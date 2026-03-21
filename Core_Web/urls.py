from django.urls import path

from .views import home_view

app_name = "Core_Web"

urlpatterns = [
    path("", home_view, name="home"),
]
