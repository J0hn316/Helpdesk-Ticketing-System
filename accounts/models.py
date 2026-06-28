from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    class Role(models.TextChoices):
        REQUESTER = "REQUESTER", "Requester"
        AGENT = "AGENT", "Agent"
        ADMIN = "ADMIN", "Administrator"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.REQUESTER,
    )

    def __str__(self) -> str:
        return self.username

    @property
    def is_requester(self) -> bool:
        return self.role == self.Role.REQUESTER

    @property
    def is_agent(self) -> bool:
        return self.role == self.Role.AGENT

    @property
    def is_helpdesk_admin(self) -> bool:
        return self.role == self.Role.ADMIN
