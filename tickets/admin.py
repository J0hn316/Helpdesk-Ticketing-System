from django.contrib import admin

from .models import Category, Ticket, TicketComment


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


class TicketCommentInline(admin.TabularInline):
    model = TicketComment
    extra = 0
    fields = (
        "author",
        "body",
        "is_internal",
        "created_at",
    )
    readonly_fields = ("created_at",)
    autocomplete_fields = ("author",)
    ordering = ("created_at",)


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

    inlines = (TicketCommentInline,)


@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = (
        "ticket",
        "author",
        "comment_type",
        "created_at",
        "updated_at",
    )
    list_filter = (
        "is_internal",
        "created_at",
    )
    search_fields = (
        "ticket__ticket_number",
        "ticket__title",
        "author__username",
        "author__email",
        "body",
    )
    autocomplete_fields = (
        "ticket",
        "author",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    @admin.display(
        description="Type",
        ordering="is_internal",
    )
    def comment_type(self, comment: TicketComment) -> str:
        if comment.is_internal:
            return "Internal note"

        return "Public comment"
