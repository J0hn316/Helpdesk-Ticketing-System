from django.urls import reverse
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError

from .forms import TicketCreateForm
from .models import Category, Ticket, TicketComment

User = get_user_model()


class CategoryModelTests(TestCase):
    def test_category_string_representation_is_name(self) -> None:
        category = Category.objects.create(
            name="Hardware",
            description="Physical devices and accessories.",
        )

        self.assertEqual(str(category), "Hardware")

    def test_category_is_active_by_default(self) -> None:
        category = Category.objects.create(
            name="Software",
        )

        self.assertTrue(category.is_active)

    def test_categories_are_ordered_alphabetically(self) -> None:
        Category.objects.create(name="Software")
        Category.objects.create(name="Hardware")
        Category.objects.create(name="Email")

        category_names = list(Category.objects.values_list("name", flat=True))

        self.assertEqual(
            category_names,
            ["Email", "Hardware", "Software"],
        )


class TicketModelTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.requester = User.objects.create_user(
            username="requester",
            password="testpass123",
            role=User.Role.REQUESTER,
        )
        cls.agent = User.objects.create_user(
            username="agent",
            password="testpass123",
            role=User.Role.AGENT,
        )
        cls.helpdesk_admin = User.objects.create_user(
            username="helpdeskadmin",
            password="testpass123",
            role=User.Role.ADMIN,
        )
        cls.other_requester = User.objects.create_user(
            username="otherrequester",
            password="testpass123",
            role=User.Role.REQUESTER,
        )
        cls.category = Category.objects.create(
            name="Hardware",
        )

    def create_ticket(self, **overrides: object) -> Ticket:
        ticket_data = {
            "title": "Laptop will not start",
            "description": "The laptop does not respond to the power button.",
            "requester": self.requester,
            "category": self.category,
        }
        ticket_data.update(overrides)

        return Ticket.objects.create(**ticket_data)

    def test_ticket_defaults_to_open_status(self) -> None:
        ticket = self.create_ticket()

        self.assertEqual(ticket.status, Ticket.Status.OPEN)

    def test_ticket_defaults_to_medium_priority(self) -> None:
        ticket = self.create_ticket()

        self.assertEqual(ticket.priority, Ticket.Priority.MEDIUM)

    def test_ticket_is_unassigned_by_default(self) -> None:
        ticket = self.create_ticket()

        self.assertIsNone(ticket.assigned_agent)

    def test_ticket_number_is_generated(self) -> None:
        ticket = self.create_ticket()

        self.assertTrue(ticket.ticket_number.startswith("HD-"))
        self.assertEqual(len(ticket.ticket_number), 11)

    def test_each_ticket_receives_a_unique_ticket_number(self) -> None:
        first_ticket = self.create_ticket(
            title="First issue",
        )
        second_ticket = self.create_ticket(
            title="Second issue",
        )

        self.assertNotEqual(
            first_ticket.ticket_number,
            second_ticket.ticket_number,
        )

    def test_ticket_string_representation_contains_number_and_title(
        self,
    ) -> None:
        ticket = self.create_ticket()

        expected_value = f"{ticket.ticket_number} - Laptop will not start"

        self.assertEqual(str(ticket), expected_value)

    def test_ticket_can_be_assigned_to_agent(self) -> None:
        ticket = self.create_ticket(
            assigned_agent=self.agent,
        )

        ticket.full_clean()

        self.assertEqual(ticket.assigned_agent, self.agent)

    def test_ticket_can_be_assigned_to_helpdesk_admin(self) -> None:
        ticket = self.create_ticket(
            assigned_agent=self.helpdesk_admin,
        )

        ticket.full_clean()

        self.assertEqual(
            ticket.assigned_agent,
            self.helpdesk_admin,
        )

    def test_ticket_cannot_be_assigned_to_requester(self) -> None:
        ticket = Ticket(
            title="Invalid assignment",
            description="Testing invalid assignment validation.",
            requester=self.requester,
            assigned_agent=self.other_requester,
            category=self.category,
        )

        with self.assertRaises(ValidationError) as context:
            ticket.full_clean()

        self.assertIn(
            "assigned_agent",
            context.exception.message_dict,
        )

    def test_requester_can_access_submitted_tickets_relationship(
        self,
    ) -> None:
        ticket = self.create_ticket()

        self.assertIn(
            ticket,
            self.requester.submitted_tickets.all(),
        )

    def test_agent_can_access_assigned_tickets_relationship(
        self,
    ) -> None:
        ticket = self.create_ticket(
            assigned_agent=self.agent,
        )

        self.assertIn(
            ticket,
            self.agent.assigned_tickets.all(),
        )

    def test_deleting_assigned_agent_unassigns_ticket(self) -> None:
        ticket = self.create_ticket(
            assigned_agent=self.agent,
        )

        self.agent.delete()
        ticket.refresh_from_db()

        self.assertIsNone(ticket.assigned_agent)

    def test_requester_with_ticket_cannot_be_deleted(self) -> None:
        self.create_ticket()

        with self.assertRaises(ProtectedError):
            self.requester.delete()

    def test_category_with_ticket_cannot_be_deleted(self) -> None:
        self.create_ticket()

        with self.assertRaises(ProtectedError):
            self.category.delete()


class TicketCommentModelTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.requester = User.objects.create_user(
            username="requester",
            password="testpass123",
            role=User.Role.REQUESTER,
        )
        cls.agent = User.objects.create_user(
            username="agent",
            password="testpass123",
            role=User.Role.AGENT,
        )
        cls.helpdesk_admin = User.objects.create_user(
            username="helpdeskadmin",
            password="testpass123",
            role=User.Role.ADMIN,
        )
        cls.category = Category.objects.create(
            name="Software",
        )
        cls.ticket = Ticket.objects.create(
            title="Application will not open",
            description=(
                "The accounting application closes immediately " "after launch."
            ),
            requester=cls.requester,
            assigned_agent=cls.agent,
            category=cls.category,
        )

    def create_comment(self, **overrides: object) -> TicketComment:
        comment_data = {
            "ticket": self.ticket,
            "author": self.requester,
            "body": "The error still occurs after restarting.",
        }
        comment_data.update(overrides)

        return TicketComment.objects.create(**comment_data)

    def test_comment_is_public_by_default(self) -> None:
        comment = self.create_comment()

        self.assertFalse(comment.is_internal)

    def test_public_comment_can_be_created_by_requester(self) -> None:
        comment = TicketComment(
            ticket=self.ticket,
            author=self.requester,
            body="I am available for troubleshooting.",
        )

        comment.full_clean()
        comment.save()

        self.assertEqual(comment.author, self.requester)
        self.assertFalse(comment.is_internal)

    def test_public_comment_can_be_created_by_agent(self) -> None:
        comment = TicketComment(
            ticket=self.ticket,
            author=self.agent,
            body="Please try launching the application again.",
        )

        comment.full_clean()
        comment.save()

        self.assertEqual(comment.author, self.agent)
        self.assertFalse(comment.is_internal)

    def test_internal_note_can_be_created_by_agent(self) -> None:
        comment = TicketComment(
            ticket=self.ticket,
            author=self.agent,
            body="Application logs show a missing configuration file.",
            is_internal=True,
        )

        comment.full_clean()
        comment.save()

        self.assertTrue(comment.is_internal)

    def test_internal_note_can_be_created_by_helpdesk_admin(
        self,
    ) -> None:
        comment = TicketComment(
            ticket=self.ticket,
            author=self.helpdesk_admin,
            body="Escalation approved.",
            is_internal=True,
        )

        comment.full_clean()
        comment.save()

        self.assertTrue(comment.is_internal)

    def test_requester_cannot_create_internal_note(self) -> None:
        comment = TicketComment(
            ticket=self.ticket,
            author=self.requester,
            body="This should not be an internal note.",
            is_internal=True,
        )

        with self.assertRaises(ValidationError) as context:
            comment.full_clean()

        self.assertIn(
            "is_internal",
            context.exception.message_dict,
        )

    def test_ticket_can_access_comments_relationship(self) -> None:
        first_comment = self.create_comment(
            body="First update.",
        )
        second_comment = self.create_comment(
            author=self.agent,
            body="Second update.",
        )

        self.assertEqual(
            list(self.ticket.comments.all()),
            [first_comment, second_comment],
        )

    def test_author_can_access_ticket_comments_relationship(
        self,
    ) -> None:
        comment = self.create_comment()

        self.assertIn(
            comment,
            self.requester.ticket_comments.all(),
        )

    def test_comments_are_ordered_oldest_first(self) -> None:
        first_comment = self.create_comment(
            body="First message.",
        )
        second_comment = self.create_comment(
            author=self.agent,
            body="Second message.",
        )

        comments = list(TicketComment.objects.all())

        self.assertEqual(
            comments,
            [first_comment, second_comment],
        )

    def test_public_comment_string_representation(self) -> None:
        comment = self.create_comment()

        expected_value = (
            f"Comment by {self.requester} " f"on {self.ticket.ticket_number}"
        )

        self.assertEqual(str(comment), expected_value)

    def test_internal_note_string_representation(self) -> None:
        comment = self.create_comment(
            author=self.agent,
            body="Internal troubleshooting information.",
            is_internal=True,
        )

        expected_value = (
            f"Internal note by {self.agent} " f"on {self.ticket.ticket_number}"
        )

        self.assertEqual(str(comment), expected_value)

    def test_deleting_ticket_deletes_its_comments(self) -> None:
        comment = self.create_comment()
        comment_id = comment.pk

        self.ticket.delete()

        self.assertFalse(TicketComment.objects.filter(pk=comment_id).exists())

    def test_comment_author_cannot_be_deleted(self) -> None:
        self.create_comment()

        with self.assertRaises(ProtectedError):
            self.requester.delete()


class TicketCreateFormTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.active_category = Category.objects.create(
            name="Hardware",
            is_active=True,
        )
        cls.inactive_category = Category.objects.create(
            name="Legacy Systems",
            is_active=False,
        )

    def valid_form_data(self) -> dict[str, object]:
        return {
            "title": "Laptop will not start",
            "description": (
                "The laptop does not respond when I press " "the power button."
            ),
            "category": self.active_category.pk,
        }

    def test_form_contains_only_requester_editable_fields(
        self,
    ) -> None:
        form = TicketCreateForm()

        self.assertEqual(
            list(form.fields),
            [
                "title",
                "description",
                "category",
            ],
        )

    def test_form_displays_only_active_categories(self) -> None:
        form = TicketCreateForm()

        category_queryset = form.fields["category"].queryset

        self.assertIn(
            self.active_category,
            category_queryset,
        )
        self.assertNotIn(
            self.inactive_category,
            category_queryset,
        )

    def test_valid_ticket_data_passes_validation(self) -> None:
        form = TicketCreateForm(
            data=self.valid_form_data(),
        )

        self.assertTrue(form.is_valid())

    def test_inactive_category_is_rejected(self) -> None:
        form_data = self.valid_form_data()
        form_data["category"] = self.inactive_category.pk

        form = TicketCreateForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn("category", form.errors)

    def test_title_is_stripped(self) -> None:
        form_data = self.valid_form_data()
        form_data["title"] = "   VPN will not connect   "

        form = TicketCreateForm(data=form_data)

        self.assertTrue(form.is_valid())
        self.assertEqual(
            form.cleaned_data["title"],
            "VPN will not connect",
        )

    def test_short_title_is_rejected(self) -> None:
        form_data = self.valid_form_data()
        form_data["title"] = "Help"

        form = TicketCreateForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

    def test_short_description_is_rejected(self) -> None:
        form_data = self.valid_form_data()
        form_data["description"] = "Broken"

        form = TicketCreateForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn("description", form.errors)


class TicketCreateViewTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.requester = User.objects.create_user(
            username="requester",
            password="testpass123",
            role=User.Role.REQUESTER,
        )
        cls.agent = User.objects.create_user(
            username="agent",
            password="testpass123",
            role=User.Role.AGENT,
        )
        cls.helpdesk_admin = User.objects.create_user(
            username="helpdeskadmin",
            password="testpass123",
            role=User.Role.ADMIN,
        )
        cls.active_category = Category.objects.create(
            name="Network",
            is_active=True,
        )
        cls.inactive_category = Category.objects.create(
            name="Legacy VPN",
            is_active=False,
        )

    def valid_ticket_data(self) -> dict[str, object]:
        return {
            "title": "Unable to connect to VPN",
            "description": (
                "The VPN reports an authentication error "
                "after I enter my credentials."
            ),
            "category": self.active_category.pk,
        }

    def test_ticket_creation_requires_authentication(self) -> None:
        response = self.client.get(
            reverse("tickets:create"),
        )

        expected_url = (
            f"{reverse('accounts:login')}" f"?next={reverse('tickets:create')}"
        )

        self.assertRedirects(
            response,
            expected_url,
        )

    def test_requester_can_view_ticket_creation_page(
        self,
    ) -> None:
        self.client.force_login(self.requester)

        response = self.client.get(
            reverse("tickets:create"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "tickets/ticket_form.html",
        )
        self.assertContains(
            response,
            "Submit a support ticket",
        )

    def test_agent_cannot_view_requester_creation_page(
        self,
    ) -> None:
        self.client.force_login(self.agent)

        response = self.client.get(
            reverse("tickets:create"),
        )

        self.assertEqual(response.status_code, 403)

    def test_helpdesk_admin_cannot_view_requester_creation_page(
        self,
    ) -> None:
        self.client.force_login(self.helpdesk_admin)

        response = self.client.get(
            reverse("tickets:create"),
        )

        self.assertEqual(response.status_code, 403)

    def test_requester_can_create_ticket(self) -> None:
        self.client.force_login(self.requester)

        response = self.client.post(
            reverse("tickets:create"),
            self.valid_ticket_data(),
        )

        ticket = Ticket.objects.get(
            title="Unable to connect to VPN",
        )

        self.assertEqual(
            ticket.requester,
            self.requester,
        )
        self.assertEqual(
            ticket.category,
            self.active_category,
        )
        self.assertRedirects(
            response,
            reverse("dashboard:home"),
        )

    def test_created_ticket_uses_safe_defaults(self) -> None:
        self.client.force_login(self.requester)

        self.client.post(
            reverse("tickets:create"),
            self.valid_ticket_data(),
        )

        ticket = Ticket.objects.get(
            title="Unable to connect to VPN",
        )

        self.assertEqual(
            ticket.status,
            Ticket.Status.OPEN,
        )
        self.assertEqual(
            ticket.priority,
            Ticket.Priority.MEDIUM,
        )
        self.assertIsNone(ticket.assigned_agent)

    def test_forged_ticket_fields_are_ignored(self) -> None:
        self.client.force_login(self.requester)

        forged_data = self.valid_ticket_data()
        forged_data.update(
            {
                "requester": self.agent.pk,
                "assigned_agent": self.agent.pk,
                "status": Ticket.Status.CLOSED,
                "priority": Ticket.Priority.CRITICAL,
                "ticket_number": "HD-FORGED01",
            }
        )

        self.client.post(
            reverse("tickets:create"),
            forged_data,
        )

        ticket = Ticket.objects.get(
            title="Unable to connect to VPN",
        )

        self.assertEqual(
            ticket.requester,
            self.requester,
        )
        self.assertIsNone(ticket.assigned_agent)
        self.assertEqual(
            ticket.status,
            Ticket.Status.OPEN,
        )
        self.assertEqual(
            ticket.priority,
            Ticket.Priority.MEDIUM,
        )
        self.assertNotEqual(
            ticket.ticket_number,
            "HD-FORGED01",
        )

    def test_inactive_category_cannot_be_submitted(self) -> None:
        self.client.force_login(self.requester)

        ticket_data = self.valid_ticket_data()
        ticket_data["category"] = self.inactive_category.pk

        response = self.client.post(
            reverse("tickets:create"),
            ticket_data,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Ticket.objects.exists())
        self.assertContains(
            response,
            "Select a valid choice",
        )

    def test_invalid_submission_does_not_create_ticket(
        self,
    ) -> None:
        self.client.force_login(self.requester)

        response = self.client.post(
            reverse("tickets:create"),
            {
                "title": "Help",
                "description": "Broken",
                "category": self.active_category.pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Ticket.objects.exists())
        self.assertContains(
            response,
            "Enter a title containing at least 5 characters.",
        )

    def test_success_message_contains_ticket_number(
        self,
    ) -> None:
        self.client.force_login(self.requester)

        response = self.client.post(
            reverse("tickets:create"),
            self.valid_ticket_data(),
            follow=True,
        )

        ticket = Ticket.objects.get(
            title="Unable to connect to VPN",
        )

        self.assertContains(
            response,
            (f"Ticket {ticket.ticket_number} was submitted " "successfully."),
        )

    def test_requester_navigation_contains_submit_link(
        self,
    ) -> None:
        self.client.force_login(self.requester)

        response = self.client.get(
            reverse("dashboard:home"),
        )

        self.assertContains(
            response,
            reverse("tickets:create"),
        )

    def test_agent_navigation_does_not_contain_submit_link(
        self,
    ) -> None:
        self.client.force_login(self.agent)

        response = self.client.get(
            reverse("dashboard:home"),
        )

        self.assertNotContains(
            response,
            reverse("tickets:create"),
        )

    def test_helpdesk_admin_navigation_does_not_contain_submit_link(
        self,
    ) -> None:
        self.client.force_login(self.helpdesk_admin)

        response = self.client.get(
            reverse("dashboard:home"),
        )

        self.assertNotContains(
            response,
            reverse("tickets:create"),
        )
