from django.urls import path

from .views import ai_test, index

app_name = "cow_calving_ai"

urlpatterns = [
    path("", index, name="index"),
    path("ai/test/", ai_test, name="ai_test"),
]

