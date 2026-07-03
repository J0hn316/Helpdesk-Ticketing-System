from django.contrib import messages
from django.db.models import Prefetch
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseForbidden,
)
from .forms import TicketCreateForm
from .models import Ticket, TicketComment


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

    public_comments = (
        TicketComment.objects.filter(is_internal=False)
        .select_related("author")
        .order_by("created_at")
    )

    ticket_queryset = Ticket.objects.select_related(
        "requester",
        "assigned_agent",
        "category",
    ).prefetch_related(
        Prefetch(
            "comments",
            queryset=public_comments,
            to_attr="public_comments",
        )
    )

    ticket = get_object_or_404(
        ticket_queryset,
        pk=ticket_id,
        requester=request.user,
    )

    context = {
        "ticket": ticket,
    }

    return render(
        request,
        "tickets/ticket_detail.html",
        context,
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
