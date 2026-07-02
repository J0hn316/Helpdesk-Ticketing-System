from django import forms

from .models import Category, Ticket


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
