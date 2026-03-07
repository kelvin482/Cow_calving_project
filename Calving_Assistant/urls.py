from django.urls import path

from .views import ai_test, index

app_name = "Calving_Assistant"

urlpatterns = [
    path("", index, name="index"),
    path("ai/test/", ai_test, name="ai_test"),
]
