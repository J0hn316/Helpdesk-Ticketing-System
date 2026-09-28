from django.urls import path

from .views import (
    ticket_list,
    ticket_claim,
    ticket_assign,
    ticket_create,
    ticket_detail,
    ticket_priority_update,
    ticket_status_update,
    agent_ticket_queue,
    agent_ticket_detail,
    support_comment_create,
    requester_comment_create,
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
        "queue/<int:ticket_id>/comments/",
        support_comment_create,
        name="support-comment-create",
    ),
    path(
        "queue/<int:ticket_id>/status/",
        ticket_status_update,
        name="status-update",
    ),
    path(
        "queue/<int:ticket_id>/priority/",
        ticket_priority_update,
        name="priority-update",
    ),
    path(
        "queue/<int:ticket_id>/claim/",
        ticket_claim,
        name="claim",
    ),
    path(
        "queue/<int:ticket_id>/assign/",
        ticket_assign,
        name="assign",
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
