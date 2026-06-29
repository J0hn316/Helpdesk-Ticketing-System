from django.contrib import messages
from django.urls import reverse_lazy
from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.views import LoginView, LogoutView

from .forms import RequesterRegistrationForm


class HelpdeskLoginView(LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True


class HelpdeskLogoutView(LogoutView):
    next_page = reverse_lazy("accounts:login")


def register(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("dashboard:home")

    if request.method == "POST":
        form = RequesterRegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)

            messages.success(
                request,
                "Your requester account was created successfully.",
            )

            return redirect("dashboard:home")
    else:
        form = RequesterRegistrationForm()

    context = {
        "form": form,
    }

    return render(
        request,
        "accounts/register.html",
        context,
    )
