from django.contrib.auth.forms import UserCreationForm

from .models import User


class RequesterRegistrationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
        )

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.role = User.Role.REQUESTER

        if commit:
            user.save()

        return user
