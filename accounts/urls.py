from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("signup/", views.register_view, name="signup"),
    path("register/", views.register_view, name="register"),
    path("password/reset/", views.password_reset_request_view, name="password_reset_request"),
    path("password/reset/done/", views.password_reset_done_redirect_view, name="password_reset_done"),
    path("password/reset/verify/", views.password_reset_verify_view, name="password_reset_verify"),
    path("logout/", views.logout_view, name="logout"),
]
