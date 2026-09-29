import uuid

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError


def generate_ticket_number() -> str:
    unique_value = uuid.uuid4().hex[:8].upper()
    return f"HD-{unique_value}"


class Category(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
    )
    description = models.TextField(
        blank=True,
    )
    is_active = models.BooleanField(
        default=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self) -> str:
        return self.name


class Ticket(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        PENDING = "PENDING", "Pending"
        RESOLVED = "RESOLVED", "Resolved"
        CLOSED = "CLOSED", "Closed"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    ticket_number = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        default=generate_ticket_number,
    )
    title = models.CharField(
        max_length=200,
    )
    description = models.TextField()
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="submitted_tickets",
    )
    assigned_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="assigned_tickets",
        null=True,
        blank=True,
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="tickets",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    closed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.ticket_number} - {self.title}"

    def clean(self) -> None:
        super().clean()

        if self.assigned_agent is None:
            return

        allowed_roles = {
            self.assigned_agent.Role.AGENT,
            self.assigned_agent.Role.ADMIN,
        }

        if self.assigned_agent.role not in allowed_roles:
            raise ValidationError(
                {
                    "assigned_agent": (
                        "Tickets can only be assigned to an agent "
                        "or helpdesk administrator."
                    )
                }
            )

    def get_allowed_status_transitions(self) -> tuple[str, ...]:
        transitions = {
            self.Status.OPEN: (
                self.Status.IN_PROGRESS,
                self.Status.PENDING,
            ),
            self.Status.IN_PROGRESS: (
                self.Status.PENDING,
                self.Status.RESOLVED,
            ),
            self.Status.PENDING: (
                self.Status.IN_PROGRESS,
                self.Status.RESOLVED,
            ),
            self.Status.RESOLVED: (
                self.Status.IN_PROGRESS,
                self.Status.CLOSED,
            ),
            self.Status.CLOSED: (),
        }

        return transitions.get(self.status, ())

    def can_transition_to(self, new_status: str) -> bool:
        return new_status in self.get_allowed_status_transitions()

    def transition_to(self, new_status: str) -> None:
        if not self.can_transition_to(new_status):
            status_labels = dict(self.Status.choices)

            current_label = status_labels.get(
                self.status,
                self.status,
            )
            new_label = status_labels.get(
                new_status,
                new_status,
            )

            raise ValidationError(
                {
                    "status": (
                        f"Cannot change ticket status from "
                        f"{current_label} to {new_label}"
                    )
                }
            )

        now = timezone.now()

        if new_status == self.Status.RESOLVED:
            self.resolved_at = now
            self.closed_at = None

        elif (
            self.status == self.Status.RESOLVED
            and new_status == self.Status.IN_PROGRESS
        ):
            self.resolved_at = None
            self.closed_at = None

        elif new_status == self.Status.CLOSED:
            if self.resolved_at is None:
                self.resolved_at = now

            self.closed_at = now

        self.status = new_status


class TicketComment(models.Model):
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="ticket_comments",
    )
    body = models.TextField()
    is_internal = models.BooleanField(
        default=False,
        help_text=(
            "Internal notes are visible only to support agents "
            "and helpdesk administrators."
        ),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        comment_type = "Internal note" if self.is_internal else "Comment"

        return f"{comment_type} by {self.author} " f"on {self.ticket.ticket_number}"

    def clean(self) -> None:
        super().clean()

        if not self.is_internal:
            return

        if not self.author_id:
            return

        allowed_roles = {
            self.author.Role.AGENT,
            self.author.Role.ADMIN,
        }

        if self.author.role not in allowed_roles:
            raise ValidationError(
                {
                    "is_internal": (
                        "Only agents and helpdesk administrators "
                        "can create internal notes."
                    )
                }
            )


class TicketHistory(models.Model):
    class Action(models.TextChoices):
        CLAIMED = "CLAIMED", "Claimed"
        ASSIGNED = "ASSIGNED", "Assigned"
        STATUS_CHANGED = "STATUS_CHANGED", "Status changed"
        PRIORITY_CHANGED = "PRIORITY_CHANGED", "Priority changed"

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="history",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="ticket_history_events",
        null=True,
        blank=True,
    )
    action = models.CharField(
        max_length=30,
        choices=Action.choices,
    )
    old_value = models.CharField(
        max_length=255,
        blank=True,
    )
    new_value = models.CharField(
        max_length=255,
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "-created_at",
            "-pk",
        ]
        verbose_name_plural = "ticket history"

    def __str__(self) -> str:
        return f"{self.ticket.ticket_number} - " f"{self.get_action_display()}"
