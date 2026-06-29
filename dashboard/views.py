from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.decorators import login_required


@login_required
def home(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "dashboard/home.html",
    )
