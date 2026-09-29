from accounts.models import User

from .models import Ticket, TicketHistory


def create_ticket_history(
    *,
    ticket: Ticket,
    actor: User | None,
    action: str,
    old_value: str = "",
    new_value: str = ""
) -> TicketHistory:
    return TicketHistory.objects.create(
        ticket=ticket,
        actor=actor,
        action=action,
        old_value=old_value,
        new_value=new_value,
    )
