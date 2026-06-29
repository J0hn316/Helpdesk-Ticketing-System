from django.urls import path

from .views import (
    HelpdeskLoginView,
    HelpdeskLogoutView,
    register,
)

app_name = "accounts"


urlpatterns = [
    path(
        "login/",
        HelpdeskLoginView.as_view(),
        name="login",
    ),
    path(
        "logout/",
        HelpdeskLogoutView.as_view(),
        name="logout",
    ),
    path(
        "register/",
        register,
        name="register",
    ),
]
