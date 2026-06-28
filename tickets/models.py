import uuid

from django.db import models
from django.conf import settings
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
