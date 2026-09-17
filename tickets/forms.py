from django import forms
from django.contrib.auth import get_user_model

from accounts.models import User
from .models import Category, Ticket, TicketComment


class TicketCreateForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = (
            "title",
            "description",
            "category",
        )
        widgets = {
            "description": forms.Textarea(
                attrs={
                    "rows": 6,
                    "placeholder": (
                        "Describe the issue, when it started, "
                        "and any troubleshooting you have tried."
                    ),
                }
            ),
        }

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)

        self.fields["category"].queryset = Category.objects.filter(is_active=True)

    def clean_title(self) -> str:
        title = self.cleaned_data["title"].strip()

        if len(title) < 5:
            raise forms.ValidationError(
                "Enter a title containing at least 5 characters."
            )

        return title

    def clean_description(self) -> str:
        description = self.cleaned_data["description"].strip()

        if len(description) < 10:
            raise forms.ValidationError(
                "Enter a description containing at least 10 characters."
            )

        return description


class RequesterCommentForm(forms.ModelForm):
    class Meta:
        model = TicketComment
        fields = ("body",)
        labels = {
            "body": "Add a reply",
        }
        widgets = {
            "body": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": (
                        "Add information, answer a support question, "
                        "or provide a troubleshooting update."
                    ),
                }
            ),
        }

    def clean_body(self) -> str:
        body = self.cleaned_data["body"].strip()

        if len(body) < 2:
            raise forms.ValidationError(
                "Enter a comment containing at least 2 characters."
            )

        return body


class TicketAssignmentForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ("assigned_agent",)
        labels = {
            "assigned_agent": "Assign to",
        }

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)

        self.fields["assigned_agent"].queryset = User.objects.filter(
            role__in=[
                User.Role.AGENT,
                User.Role.ADMIN,
            ]
        ).order_by("username")

        self.fields["assigned_agent"].required = True

    def clean_assigned_agent(self) -> User:
        assigned_agent = self.cleaned_data["assigned_agent"]

        if not assigned_agent.is_support_staff:
            raise forms.ValidationError(
                "Tickets can only be assigned to support staff."
            )

        return assigned_agent
