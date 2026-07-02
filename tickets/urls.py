from django.urls import path

from .views import ticket_create

app_name = "tickets"


urlpatterns = [
    path(
        "new/",
        ticket_create,
        name="create",
    ),
]
