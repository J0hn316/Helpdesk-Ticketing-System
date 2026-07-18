from django.urls import path

from .views import (
    ticket_create,
    ticket_detail,
    ticket_list,
    requester_comment_create,
    agent_ticket_detail,
    agent_ticket_queue,
)

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
        "queue/",
        agent_ticket_queue,
        name="agent-queue",
    ),
    path(
        "queue/<int:ticket_id>/",
        agent_ticket_detail,
        name="agent-detail",
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
