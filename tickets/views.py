from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseForbidden,
)
from .models import Ticket
from .forms import TicketCreateForm


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

            return redirect("dashboard:home")
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
