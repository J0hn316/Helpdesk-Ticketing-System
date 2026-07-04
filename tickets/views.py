from django.contrib import messages
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render, get_object_or_404
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseForbidden,
)

from .models import Ticket, TicketComment
from .forms import TicketCreateForm, RequesterCommentForm


@login_required
def ticket_list(request: HttpRequest) -> HttpResponse:
    if not request.user.is_requester:
        return HttpResponseForbidden("Only requesters can view this ticket list.")

    tickets = (
        Ticket.objects.filter(requester=request.user)
        .select_related(
            "category",
            "assigned_agent",
        )
        .order_by("-created_at")
    )

    context = {"tickets": tickets}

    return render(
        request,
        "tickets/ticket_list.html",
        context,
    )


@login_required
def ticket_detail(
    request: HttpRequest,
    ticket_id: int,
) -> HttpResponse:
    if not request.user.is_requester:
        return HttpResponseForbidden("Only requesters can view this ticket page.")

    ticket = get_object_or_404(
        Ticket.objects.select_related(
            "requester",
            "assigned_agent",
            "category",
        ),
        pk=ticket_id,
        requester=request.user,
    )

    public_comments = (
        ticket.comments.filter(is_internal=False)
        .select_related("author")
        .order_by("created_at")
    )

    context = {
        "ticket": ticket,
        "public_comments": public_comments,
        "comment_form": RequesterCommentForm(),
        "can_comment": ticket.status != Ticket.Status.CLOSED,
    }

    return render(
        request,
        "tickets/ticket_detail.html",
        context,
    )


@login_required
@require_POST
def requester_comment_create(
    request: HttpRequest,
    ticket_id: int,
) -> HttpResponse:
    if not request.user.is_requester:
        return HttpResponseForbidden(
            "Only requesters can add comments through this page."
        )

    ticket = get_object_or_404(
        Ticket,
        pk=ticket_id,
        requester=request.user,
    )

    if ticket.status == Ticket.Status.CLOSED:
        messages.error(
            request,
            "Closed tickets cannot receive new requester comments.",
        )

        return redirect(
            "tickets:detail",
            ticket_id=ticket.pk,
        )

    form = RequesterCommentForm(request.POST)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.ticket = ticket
        comment.author = request.user
        comment.is_internal = False
        comment.full_clean()
        comment.save()

        messages.success(
            request,
            "Your reply was added successfully.",
        )

        return redirect(
            "tickets:detail",
            ticket_id=ticket.pk,
        )

    public_comments = (
        TicketComment.objects.filter(
            ticket=ticket,
            is_internal=False,
        )
        .select_related("author")
        .order_by("created_at")
    )

    context = {
        "ticket": ticket,
        "comment_form": form,
        "public_comments": public_comments,
        "can_comment": True,
    }

    return render(
        request,
        "tickets/ticket_detail.html",
        context,
        status=400,
    )


@login_required
def ticket_create(request: HttpRequest) -> HttpResponse:
    if not request.user.is_requester:
        return HttpResponseForbidden(
            "Only requesters can submit tickets through this page."
        )

    if request.method == "POST":
        form = TicketCreateForm(request.POST)

        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.requester = request.user
            ticket.status = Ticket.Status.OPEN
            ticket.priority = Ticket.Priority.MEDIUM
            ticket.assigned_agent = None
            ticket.full_clean()
            ticket.save()

            messages.success(
                request,
                (f"Ticket {ticket.ticket_number} was submitted " "successfully."),
            )

            return redirect(
                "tickets:detail",
                ticket_id=ticket.pk,
            )
    else:
        form = TicketCreateForm()

    context = {
        "form": form,
    }

    return render(
        request,
        "tickets/ticket_form.html",
        context,
    )
