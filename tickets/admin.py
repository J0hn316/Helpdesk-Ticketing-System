from django.contrib import admin

from .models import Category, Ticket


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "is_active",
        "created_at",
        "updated_at",
    )
    list_filter = ("is_active",)
    search_fields = (
        "name",
        "description",
    )
    ordering = ("name",)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "ticket_number",
        "title",
        "requester",
        "assigned_agent",
        "category",
        "status",
        "priority",
        "created_at",
    )
    list_filter = (
        "status",
        "priority",
        "category",
        "created_at",
    )
    search_fields = (
        "ticket_number",
        "title",
        "description",
        "requester__username",
        "requester__email",
        "assigned_agent__username",
    )
    readonly_fields = (
        "ticket_number",
        "created_at",
        "updated_at",
        "resolved_at",
        "closed_at",
    )
    autocomplete_fields = (
        "requester",
        "assigned_agent",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
