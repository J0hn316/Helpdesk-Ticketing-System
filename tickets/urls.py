from django.urls import path

from .views import ticket_create, ticket_detail, ticket_list, requester_comment_create

app_name = "tickets"


urlpatterns = [
    path(
        "",
        ticket_list,
        name="list",
    ),
    path(
        "new/",
        ticket_create,
        name="create",
    ),
    path(
        "<int:ticket_id>/",
        ticket_detail,
        name="detail",
    ),
    path(
        "<int:ticket_id>/comments/",
        requester_comment_create,
        name="comment-create",
    ),
]
