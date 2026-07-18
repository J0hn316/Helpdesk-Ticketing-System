from django.urls import reverse
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError

from .forms import TicketCreateForm, RequesterCommentForm
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
            reverse(
                "tickets:detail",
                kwargs={"ticket_id": ticket.pk},
            ),
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


class RequesterTicketListViewTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.requester = User.objects.create_user(
            username="requester",
            password="testpass123",
            role=User.Role.REQUESTER,
        )
        cls.other_requester = User.objects.create_user(
            username="otherrequester",
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
            name="Hardware",
        )

        cls.requester_ticket = Ticket.objects.create(
            title="Requester laptop issue",
            description=("The requester laptop does not start correctly."),
            requester=cls.requester,
            category=cls.category,
        )
        cls.other_ticket = Ticket.objects.create(
            title="Another user's ticket",
            description=("This ticket belongs to another requester."),
            requester=cls.other_requester,
            category=cls.category,
        )

    def test_ticket_list_requires_authentication(self) -> None:
        response = self.client.get(
            reverse("tickets:list"),
        )

        expected_url = f"{reverse('accounts:login')}" f"?next={reverse('tickets:list')}"

        self.assertRedirects(
            response,
            expected_url,
        )

    def test_requester_can_view_ticket_list(self) -> None:
        self.client.force_login(self.requester)

        response = self.client.get(
            reverse("tickets:list"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "tickets/ticket_list.html",
        )
        self.assertContains(response, "My tickets")

    def test_requester_sees_only_their_own_tickets(self) -> None:
        self.client.force_login(self.requester)

        response = self.client.get(
            reverse("tickets:list"),
        )

        self.assertContains(
            response,
            self.requester_ticket.ticket_number,
        )
        self.assertContains(
            response,
            self.requester_ticket.title,
        )
        self.assertNotContains(
            response,
            self.other_ticket.ticket_number,
        )
        self.assertNotContains(
            response,
            self.other_ticket.title,
        )

    def test_ticket_list_context_contains_only_owned_tickets(
        self,
    ) -> None:
        self.client.force_login(self.requester)

        response = self.client.get(
            reverse("tickets:list"),
        )

        tickets = list(response.context["tickets"])

        self.assertEqual(
            tickets,
            [self.requester_ticket],
        )

    def test_agent_cannot_view_requester_ticket_list(
        self,
    ) -> None:
        self.client.force_login(self.agent)

        response = self.client.get(
            reverse("tickets:list"),
        )

        self.assertEqual(response.status_code, 403)

    def test_helpdesk_admin_cannot_view_requester_ticket_list(
        self,
    ) -> None:
        self.client.force_login(self.helpdesk_admin)

        response = self.client.get(
            reverse("tickets:list"),
        )

        self.assertEqual(response.status_code, 403)

    def test_empty_ticket_list_displays_empty_state(self) -> None:
        requester_without_tickets = User.objects.create_user(
            username="emptyrequester",
            password="testpass123",
            role=User.Role.REQUESTER,
        )
        self.client.force_login(requester_without_tickets)

        response = self.client.get(
            reverse("tickets:list"),
        )

        self.assertContains(response, "No tickets yet")
        self.assertContains(
            response,
            "Submit your first ticket",
        )

    def test_ticket_list_displays_status_and_priority(
        self,
    ) -> None:
        self.client.force_login(self.requester)

        response = self.client.get(
            reverse("tickets:list"),
        )

        self.assertContains(
            response,
            self.requester_ticket.get_status_display(),
        )
        self.assertContains(
            response,
            self.requester_ticket.get_priority_display(),
        )

    def test_ticket_list_contains_detail_link(self) -> None:
        self.client.force_login(self.requester)

        response = self.client.get(
            reverse("tickets:list"),
        )

        detail_url = reverse(
            "tickets:detail",
            kwargs={
                "ticket_id": self.requester_ticket.pk,
            },
        )

        self.assertContains(response, detail_url)

    def test_requester_navigation_contains_ticket_list_link(
        self,
    ) -> None:
        self.client.force_login(self.requester)

        response = self.client.get(
            reverse("dashboard:home"),
        )

        self.assertContains(
            response,
            reverse("tickets:list"),
        )

    def test_agent_navigation_does_not_contain_ticket_list_link(
        self,
    ) -> None:
        self.client.force_login(self.agent)

        response = self.client.get(
            reverse("dashboard:home"),
        )
        requester_ticket_list_link = f'href="{reverse("tickets:list")}"'

        self.assertNotContains(
            response,
            requester_ticket_list_link,
        )

    def test_helpdesk_admin_navigation_does_not_contain_ticket_list_link(
        self,
    ) -> None:
        self.client.force_login(self.helpdesk_admin)

        response = self.client.get(
            reverse("dashboard:home"),
        )
        requester_ticket_list_link = f'href="{reverse("tickets:list")}"'

        self.assertNotContains(
            response,
            requester_ticket_list_link,
        )


class RequesterTicketDetailViewTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.requester = User.objects.create_user(
            username="requester",
            password="testpass123",
            role=User.Role.REQUESTER,
        )
        cls.other_requester = User.objects.create_user(
            username="otherrequester",
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
            name="Network",
        )
        cls.ticket = Ticket.objects.create(
            title="VPN authentication error",
            description=(
                "The VPN reports an authentication error "
                "when the requester attempts to connect."
            ),
            requester=cls.requester,
            assigned_agent=cls.agent,
            category=cls.category,
            priority=Ticket.Priority.HIGH,
        )
        cls.other_ticket = Ticket.objects.create(
            title="Other requester issue",
            description=("This ticket belongs to another requester."),
            requester=cls.other_requester,
            category=cls.category,
        )
        cls.requester_comment = TicketComment.objects.create(
            ticket=cls.ticket,
            author=cls.requester,
            body="The issue still happens after restarting.",
        )
        cls.agent_public_comment = TicketComment.objects.create(
            ticket=cls.ticket,
            author=cls.agent,
            body="Please reset your network password and retry.",
        )
        cls.internal_note = TicketComment.objects.create(
            ticket=cls.ticket,
            author=cls.agent,
            body=(
                "Account appears locked in the identity system. "
                "Do not expose this internal note."
            ),
            is_internal=True,
        )

    def detail_url(self, ticket: Ticket | None = None) -> str:
        selected_ticket = ticket or self.ticket

        return reverse(
            "tickets:detail",
            kwargs={
                "ticket_id": selected_ticket.pk,
            },
        )

    def test_ticket_detail_requires_authentication(self) -> None:
        response = self.client.get(
            self.detail_url(),
        )

        expected_url = f"{reverse('accounts:login')}" f"?next={self.detail_url()}"

        self.assertRedirects(
            response,
            expected_url,
        )

    def test_requester_can_view_owned_ticket(self) -> None:
        self.client.force_login(self.requester)

        response = self.client.get(
            self.detail_url(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "tickets/ticket_detail.html",
        )
        self.assertContains(
            response,
            self.ticket.ticket_number,
        )
        self.assertContains(
            response,
            self.ticket.title,
        )
        self.assertContains(
            response,
            self.ticket.description,
        )

    def test_requester_cannot_view_another_requesters_ticket(
        self,
    ) -> None:
        self.client.force_login(self.requester)

        response = self.client.get(
            self.detail_url(self.other_ticket),
        )

        self.assertEqual(response.status_code, 404)

    def test_nonexistent_ticket_returns_404(self) -> None:
        self.client.force_login(self.requester)

        response = self.client.get(
            reverse(
                "tickets:detail",
                kwargs={"ticket_id": 999999},
            ),
        )

        self.assertEqual(response.status_code, 404)

    def test_agent_cannot_view_requester_detail_page(
        self,
    ) -> None:
        self.client.force_login(self.agent)

        response = self.client.get(
            self.detail_url(),
        )

        self.assertEqual(response.status_code, 403)

    def test_helpdesk_admin_cannot_view_requester_detail_page(
        self,
    ) -> None:
        self.client.force_login(self.helpdesk_admin)

        response = self.client.get(
            self.detail_url(),
        )

        self.assertEqual(response.status_code, 403)

    def test_ticket_detail_displays_ticket_metadata(
        self,
    ) -> None:
        self.client.force_login(self.requester)

        response = self.client.get(
            self.detail_url(),
        )

        self.assertContains(
            response,
            self.ticket.get_status_display(),
        )
        self.assertContains(
            response,
            self.ticket.get_priority_display(),
        )
        self.assertContains(
            response,
            self.category.name,
        )
        self.assertContains(
            response,
            self.agent.username,
        )

    def test_ticket_detail_displays_public_comments(
        self,
    ) -> None:
        self.client.force_login(self.requester)

        response = self.client.get(
            self.detail_url(),
        )

        self.assertContains(
            response,
            self.requester_comment.body,
        )
        self.assertContains(
            response,
            self.agent_public_comment.body,
        )

    def test_ticket_detail_hides_internal_notes(
        self,
    ) -> None:
        self.client.force_login(self.requester)

        response = self.client.get(
            self.detail_url(),
        )

        self.assertNotContains(
            response,
            self.internal_note.body,
        )

    def test_public_comments_context_excludes_internal_notes(
        self,
    ) -> None:
        self.client.force_login(self.requester)

        response = self.client.get(
            self.detail_url(),
        )

        public_comments = list(response.context["public_comments"])

        self.assertEqual(
            public_comments,
            [
                self.requester_comment,
                self.agent_public_comment,
            ],
        )
        self.assertNotIn(
            self.internal_note,
            public_comments,
        )

    def test_public_comments_are_oldest_first(self) -> None:
        self.client.force_login(self.requester)

        response = self.client.get(
            self.detail_url(),
        )

        public_comments = list(response.context["public_comments"])

        self.assertEqual(
            public_comments,
            [
                self.requester_comment,
                self.agent_public_comment,
            ],
        )

    def test_ticket_without_comments_displays_empty_message(
        self,
    ) -> None:
        ticket_without_comments = Ticket.objects.create(
            title="No conversation ticket",
            description=("This ticket does not have any comments yet."),
            requester=self.requester,
            category=self.category,
        )
        self.client.force_login(self.requester)

        response = self.client.get(
            self.detail_url(ticket_without_comments),
        )

        self.assertContains(
            response,
            "No public updates have been added to this ticket.",
        )

    def test_open_ticket_displays_comment_form(self) -> None:
        self.client.force_login(self.requester)

        response = self.client.get(
            self.detail_url(),
        )

        self.assertContains(response, "Add a reply")
        self.assertContains(
            response,
            reverse(
                "tickets:comment-create",
                kwargs={"ticket_id": self.ticket.pk},
            ),
        )
        self.assertIsInstance(
            response.context["comment_form"],
            RequesterCommentForm,
        )

    def test_closed_ticket_hides_comment_form(self) -> None:
        closed_ticket = Ticket.objects.create(
            title="Closed network issue",
            description=("This network issue has completed the workflow."),
            requester=self.requester,
            category=self.category,
            status=Ticket.Status.CLOSED,
        )
        self.client.force_login(self.requester)

        response = self.client.get(
            self.detail_url(closed_ticket),
        )

        self.assertContains(
            response,
            "This ticket is closed and cannot receive new replies.",
        )
        self.assertNotContains(
            response,
            reverse(
                "tickets:comment-create",
                kwargs={"ticket_id": closed_ticket.pk},
            ),
        )


class RequesterCommentCreateViewTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.requester = User.objects.create_user(
            username="requester",
            password="testpass123",
            role=User.Role.REQUESTER,
        )
        cls.other_requester = User.objects.create_user(
            username="otherrequester",
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
            title="Application login failure",
            description=(
                "The application rejects the requester's " "valid login credentials."
            ),
            requester=cls.requester,
            assigned_agent=cls.agent,
            category=cls.category,
        )
        cls.other_ticket = Ticket.objects.create(
            title="Other requester's application issue",
            description=("This ticket belongs to another requester."),
            requester=cls.other_requester,
            category=cls.category,
        )
        cls.closed_ticket = Ticket.objects.create(
            title="Closed software issue",
            description=("This ticket has already completed its workflow."),
            requester=cls.requester,
            category=cls.category,
            status=Ticket.Status.CLOSED,
        )

    def comment_url(self, ticket: Ticket | None = None) -> str:
        selected_ticket = ticket or self.ticket

        return reverse(
            "tickets:comment-create",
            kwargs={
                "ticket_id": selected_ticket.pk,
            },
        )

    def valid_comment_data(self) -> dict[str, str]:
        return {
            "body": (
                "The problem still happens after reinstalling " "the application."
            ),
        }

    def test_comment_creation_requires_authentication(self) -> None:
        response = self.client.post(
            self.comment_url(),
            self.valid_comment_data(),
        )

        expected_url = f"{reverse('accounts:login')}" f"?next={self.comment_url()}"

        self.assertRedirects(
            response,
            expected_url,
        )

    def test_comment_endpoint_does_not_accept_get(self) -> None:
        self.client.force_login(self.requester)

        response = self.client.get(
            self.comment_url(),
        )

        self.assertEqual(response.status_code, 405)

    def test_requester_can_add_comment_to_owned_ticket(
        self,
    ) -> None:
        self.client.force_login(self.requester)

        response = self.client.post(
            self.comment_url(),
            self.valid_comment_data(),
        )

        comment = TicketComment.objects.get(
            body=("The problem still happens after reinstalling " "the application."),
        )

        self.assertEqual(comment.ticket, self.ticket)
        self.assertEqual(comment.author, self.requester)
        self.assertFalse(comment.is_internal)

        self.assertRedirects(
            response,
            reverse(
                "tickets:detail",
                kwargs={"ticket_id": self.ticket.pk},
            ),
        )

    def test_success_message_is_displayed(self) -> None:
        self.client.force_login(self.requester)

        response = self.client.post(
            self.comment_url(),
            self.valid_comment_data(),
            follow=True,
        )

        self.assertContains(
            response,
            "Your reply was added successfully.",
        )

    def test_requester_cannot_comment_on_another_users_ticket(
        self,
    ) -> None:
        self.client.force_login(self.requester)

        response = self.client.post(
            self.comment_url(self.other_ticket),
            self.valid_comment_data(),
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(
            TicketComment.objects.filter(
                ticket=self.other_ticket,
                author=self.requester,
            ).exists()
        )

    def test_nonexistent_ticket_returns_404(self) -> None:
        self.client.force_login(self.requester)

        response = self.client.post(
            reverse(
                "tickets:comment-create",
                kwargs={"ticket_id": 999999},
            ),
            self.valid_comment_data(),
        )

        self.assertEqual(response.status_code, 404)

    def test_agent_cannot_use_requester_comment_endpoint(
        self,
    ) -> None:
        self.client.force_login(self.agent)

        response = self.client.post(
            self.comment_url(),
            self.valid_comment_data(),
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(TicketComment.objects.exists())

    def test_helpdesk_admin_cannot_use_requester_comment_endpoint(
        self,
    ) -> None:
        self.client.force_login(self.helpdesk_admin)

        response = self.client.post(
            self.comment_url(),
            self.valid_comment_data(),
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(TicketComment.objects.exists())

    def test_forged_author_is_ignored(self) -> None:
        self.client.force_login(self.requester)

        forged_data = self.valid_comment_data()
        forged_data["author"] = str(self.agent.pk)

        self.client.post(
            self.comment_url(),
            forged_data,
        )

        comment = TicketComment.objects.get()

        self.assertEqual(comment.author, self.requester)

    def test_forged_ticket_is_ignored(self) -> None:
        self.client.force_login(self.requester)

        forged_data = self.valid_comment_data()
        forged_data["ticket"] = str(self.other_ticket.pk)

        self.client.post(
            self.comment_url(),
            forged_data,
        )

        comment = TicketComment.objects.get()

        self.assertEqual(comment.ticket, self.ticket)
        self.assertNotEqual(
            comment.ticket,
            self.other_ticket,
        )

    def test_forged_internal_value_is_ignored(self) -> None:
        self.client.force_login(self.requester)

        forged_data = self.valid_comment_data()
        forged_data["is_internal"] = "true"

        self.client.post(
            self.comment_url(),
            forged_data,
        )

        comment = TicketComment.objects.get()

        self.assertFalse(comment.is_internal)

    def test_invalid_comment_is_not_created(self) -> None:
        self.client.force_login(self.requester)

        response = self.client.post(
            self.comment_url(),
            {"body": "x"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(TicketComment.objects.exists())
        self.assertContains(
            response,
            "Enter a comment containing at least 2 characters.",
            status_code=400,
        )

    def test_invalid_comment_preserves_submitted_body(
        self,
    ) -> None:
        self.client.force_login(self.requester)

        response = self.client.post(
            self.comment_url(),
            {"body": "x"},
        )

        self.assertEqual(
            response.context["comment_form"]["body"].value(),
            "x",
        )

    def test_invalid_comment_page_still_hides_internal_notes(
        self,
    ) -> None:
        TicketComment.objects.create(
            ticket=self.ticket,
            author=self.agent,
            body="Private technician troubleshooting details.",
            is_internal=True,
        )
        self.client.force_login(self.requester)

        response = self.client.post(
            self.comment_url(),
            {"body": "x"},
        )

        self.assertNotContains(
            response,
            "Private technician troubleshooting details.",
            status_code=400,
        )

    def test_closed_ticket_rejects_new_comment(self) -> None:
        self.client.force_login(self.requester)

        response = self.client.post(
            self.comment_url(self.closed_ticket),
            self.valid_comment_data(),
        )

        self.assertRedirects(
            response,
            reverse(
                "tickets:detail",
                kwargs={"ticket_id": self.closed_ticket.pk},
            ),
        )
        self.assertFalse(
            TicketComment.objects.filter(
                ticket=self.closed_ticket,
            ).exists()
        )

    def test_closed_ticket_displays_error_message(self) -> None:
        self.client.force_login(self.requester)

        response = self.client.post(
            self.comment_url(self.closed_ticket),
            self.valid_comment_data(),
            follow=True,
        )

        self.assertContains(
            response,
            "Closed tickets cannot receive new requester comments.",
        )


class RequesterCommentFormTests(TestCase):
    def test_form_contains_only_body_field(self) -> None:
        form = RequesterCommentForm()

        self.assertEqual(
            list(form.fields),
            ["body"],
        )

    def test_valid_body_passes_validation(self) -> None:
        form = RequesterCommentForm(
            data={
                "body": ("The error still appears after restarting."),
            }
        )

        self.assertTrue(form.is_valid())

    def test_body_is_stripped(self) -> None:
        form = RequesterCommentForm(
            data={
                "body": "   The issue still happens.   ",
            }
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(
            form.cleaned_data["body"],
            "The issue still happens.",
        )

    def test_empty_body_is_rejected(self) -> None:
        form = RequesterCommentForm(
            data={"body": ""},
        )

        self.assertFalse(form.is_valid())
        self.assertIn("body", form.errors)

    def test_whitespace_only_body_is_rejected(self) -> None:
        form = RequesterCommentForm(
            data={"body": "      "},
        )

        self.assertFalse(form.is_valid())
        self.assertIn("body", form.errors)

    def test_one_character_body_is_rejected(self) -> None:
        form = RequesterCommentForm(
            data={"body": "x"},
        )

        self.assertFalse(form.is_valid())
        self.assertIn("body", form.errors)

    def test_forged_fields_are_not_form_fields(self) -> None:
        form = RequesterCommentForm()

        self.assertNotIn("ticket", form.fields)
        self.assertNotIn("author", form.fields)
        self.assertNotIn("is_internal", form.fields)


class AgentTicketQueueViewTests(TestCase):
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
            name="Network",
        )

        cls.open_ticket = Ticket.objects.create(
            title="Open network issue",
            description=("The requester cannot connect to the network."),
            requester=cls.requester,
            category=cls.category,
            status=Ticket.Status.OPEN,
        )
        cls.in_progress_ticket = Ticket.objects.create(
            title="In-progress network issue",
            description=("An agent is currently investigating this issue."),
            requester=cls.requester,
            assigned_agent=cls.agent,
            category=cls.category,
            status=Ticket.Status.IN_PROGRESS,
            priority=Ticket.Priority.HIGH,
        )
        cls.resolved_ticket = Ticket.objects.create(
            title="Resolved network issue",
            description=("Support believes this issue has been resolved."),
            requester=cls.requester,
            assigned_agent=cls.agent,
            category=cls.category,
            status=Ticket.Status.RESOLVED,
        )
        cls.closed_ticket = Ticket.objects.create(
            title="Closed network issue",
            description=("This issue has completed the support workflow."),
            requester=cls.requester,
            assigned_agent=cls.agent,
            category=cls.category,
            status=Ticket.Status.CLOSED,
        )

    def test_agent_queue_requires_authentication(self) -> None:
        response = self.client.get(
            reverse("tickets:agent-queue"),
        )

        expected_url = (
            f"{reverse('accounts:login')}" f"?next={reverse('tickets:agent-queue')}"
        )

        self.assertRedirects(
            response,
            expected_url,
        )

    def test_requester_cannot_view_agent_queue(self) -> None:
        self.client.force_login(self.requester)

        response = self.client.get(
            reverse("tickets:agent-queue"),
        )

        self.assertEqual(response.status_code, 403)

    def test_agent_can_view_queue(self) -> None:
        self.client.force_login(self.agent)

        response = self.client.get(
            reverse("tickets:agent-queue"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "tickets/agent_ticket_queue.html",
        )
        self.assertContains(response, "Support queue")

    def test_helpdesk_admin_can_view_queue(self) -> None:
        self.client.force_login(self.helpdesk_admin)

        response = self.client.get(
            reverse("tickets:agent-queue"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Support queue")

    def test_queue_contains_non_closed_tickets(self) -> None:
        self.client.force_login(self.agent)

        response = self.client.get(
            reverse("tickets:agent-queue"),
        )

        self.assertContains(
            response,
            self.open_ticket.ticket_number,
        )
        self.assertContains(
            response,
            self.in_progress_ticket.ticket_number,
        )
        self.assertContains(
            response,
            self.resolved_ticket.ticket_number,
        )

    def test_queue_excludes_closed_tickets(self) -> None:
        self.client.force_login(self.agent)

        response = self.client.get(
            reverse("tickets:agent-queue"),
        )

        self.assertNotContains(
            response,
            self.closed_ticket.ticket_number,
        )
        self.assertNotContains(
            response,
            self.closed_ticket.title,
        )

    def test_queue_context_excludes_closed_tickets(self) -> None:
        self.client.force_login(self.agent)

        response = self.client.get(
            reverse("tickets:agent-queue"),
        )

        tickets = list(response.context["tickets"])

        self.assertIn(self.open_ticket, tickets)
        self.assertIn(self.in_progress_ticket, tickets)
        self.assertIn(self.resolved_ticket, tickets)
        self.assertNotIn(self.closed_ticket, tickets)

    def test_queue_displays_ticket_metadata(self) -> None:
        self.client.force_login(self.agent)

        response = self.client.get(
            reverse("tickets:agent-queue"),
        )

        self.assertContains(
            response,
            self.requester.username,
        )
        self.assertContains(
            response,
            self.category.name,
        )
        self.assertContains(
            response,
            self.in_progress_ticket.get_status_display(),
        )
        self.assertContains(
            response,
            self.in_progress_ticket.get_priority_display(),
        )

    def test_queue_marks_unassigned_ticket(self) -> None:
        self.client.force_login(self.agent)

        response = self.client.get(
            reverse("tickets:agent-queue"),
        )

        self.assertContains(response, "Unassigned")

    def test_queue_contains_agent_detail_links(self) -> None:
        self.client.force_login(self.agent)

        response = self.client.get(
            reverse("tickets:agent-queue"),
        )

        detail_url = reverse(
            "tickets:agent-detail",
            kwargs={"ticket_id": self.open_ticket.pk},
        )

        self.assertContains(response, detail_url)

    def test_empty_queue_displays_empty_state(self) -> None:
        Ticket.objects.exclude(status=Ticket.Status.CLOSED).delete()

        self.client.force_login(self.agent)

        response = self.client.get(
            reverse("tickets:agent-queue"),
        )

        self.assertContains(response, "No active tickets")

    def test_agent_navigation_contains_queue_link(self) -> None:
        self.client.force_login(self.agent)

        response = self.client.get(
            reverse("dashboard:home"),
        )

        self.assertContains(
            response,
            reverse("tickets:agent-queue"),
        )

    def test_helpdesk_admin_navigation_contains_queue_link(
        self,
    ) -> None:
        self.client.force_login(self.helpdesk_admin)

        response = self.client.get(
            reverse("dashboard:home"),
        )

        self.assertContains(
            response,
            reverse("tickets:agent-queue"),
        )

    def test_requester_navigation_does_not_contain_queue_link(
        self,
    ) -> None:
        self.client.force_login(self.requester)

        response = self.client.get(
            reverse("dashboard:home"),
        )

        self.assertNotContains(
            response,
            reverse("tickets:agent-queue"),
        )


class AgentTicketDetailViewTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.requester = User.objects.create_user(
            username="requester",
            email="requester@example.com",
            password="testpass123",
            role=User.Role.REQUESTER,
        )
        cls.agent = User.objects.create_user(
            username="agent",
            password="testpass123",
            role=User.Role.AGENT,
        )
        cls.other_agent = User.objects.create_user(
            username="otheragent",
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
            title="Accounting application error",
            description=("The application closes immediately after login."),
            requester=cls.requester,
            assigned_agent=cls.other_agent,
            category=cls.category,
            status=Ticket.Status.IN_PROGRESS,
            priority=Ticket.Priority.HIGH,
        )
        cls.closed_ticket = Ticket.objects.create(
            title="Previously closed software issue",
            description=("This ticket is available for historical review."),
            requester=cls.requester,
            assigned_agent=cls.agent,
            category=cls.category,
            status=Ticket.Status.CLOSED,
        )
        cls.requester_comment = TicketComment.objects.create(
            ticket=cls.ticket,
            author=cls.requester,
            body="The error still occurs after restarting.",
        )
        cls.public_agent_comment = TicketComment.objects.create(
            ticket=cls.ticket,
            author=cls.agent,
            body="Please reinstall the application.",
        )
        cls.internal_note = TicketComment.objects.create(
            ticket=cls.ticket,
            author=cls.agent,
            body=("Application logs show a missing configuration file."),
            is_internal=True,
        )

    def detail_url(self, ticket: Ticket | None = None) -> str:
        selected_ticket = ticket or self.ticket

        return reverse(
            "tickets:agent-detail",
            kwargs={"ticket_id": selected_ticket.pk},
        )

    def test_agent_detail_requires_authentication(self) -> None:
        response = self.client.get(
            self.detail_url(),
        )

        expected_url = f"{reverse('accounts:login')}" f"?next={self.detail_url()}"

        self.assertRedirects(
            response,
            expected_url,
        )

    def test_requester_cannot_view_agent_detail(self) -> None:
        self.client.force_login(self.requester)

        response = self.client.get(
            self.detail_url(),
        )

        self.assertEqual(response.status_code, 403)

    def test_agent_can_view_any_ticket(self) -> None:
        self.client.force_login(self.agent)

        response = self.client.get(
            self.detail_url(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "tickets/agent_ticket_detail.html",
        )
        self.assertContains(
            response,
            self.ticket.ticket_number,
        )

    def test_helpdesk_admin_can_view_any_ticket(self) -> None:
        self.client.force_login(self.helpdesk_admin)

        response = self.client.get(
            self.detail_url(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            self.ticket.ticket_number,
        )

    def test_agent_can_view_ticket_assigned_to_another_agent(
        self,
    ) -> None:
        self.client.force_login(self.agent)

        response = self.client.get(
            self.detail_url(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            self.other_agent.username,
        )

    def test_agent_can_view_closed_ticket_directly(self) -> None:
        self.client.force_login(self.agent)

        response = self.client.get(
            self.detail_url(self.closed_ticket),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            self.closed_ticket.ticket_number,
        )
        self.assertContains(response, "Closed")

    def test_nonexistent_ticket_returns_404(self) -> None:
        self.client.force_login(self.agent)

        response = self.client.get(
            reverse(
                "tickets:agent-detail",
                kwargs={"ticket_id": 999999},
            ),
        )

        self.assertEqual(response.status_code, 404)

    def test_detail_displays_ticket_metadata(self) -> None:
        self.client.force_login(self.agent)

        response = self.client.get(
            self.detail_url(),
        )

        self.assertContains(
            response,
            self.requester.username,
        )
        self.assertContains(
            response,
            self.requester.email,
        )
        self.assertContains(
            response,
            self.ticket.get_status_display(),
        )
        self.assertContains(
            response,
            self.ticket.get_priority_display(),
        )
        self.assertContains(
            response,
            self.category.name,
        )
        self.assertContains(
            response,
            self.other_agent.username,
        )

    def test_detail_displays_public_comments(self) -> None:
        self.client.force_login(self.agent)

        response = self.client.get(
            self.detail_url(),
        )

        self.assertContains(
            response,
            self.requester_comment.body,
        )
        self.assertContains(
            response,
            self.public_agent_comment.body,
        )

    def test_detail_displays_internal_notes(self) -> None:
        self.client.force_login(self.agent)

        response = self.client.get(
            self.detail_url(),
        )

        self.assertContains(
            response,
            self.internal_note.body,
        )
        self.assertContains(response, "Internal note")

    def test_comments_are_oldest_first(self) -> None:
        self.client.force_login(self.agent)

        response = self.client.get(
            self.detail_url(),
        )

        comments = list(response.context["comments"])

        self.assertEqual(
            comments,
            [
                self.requester_comment,
                self.public_agent_comment,
                self.internal_note,
            ],
        )

    def test_ticket_without_comments_displays_empty_message(
        self,
    ) -> None:
        ticket_without_comments = Ticket.objects.create(
            title="Ticket without conversation",
            description=("No one has added a comment to this ticket."),
            requester=self.requester,
            category=self.category,
        )
        self.client.force_login(self.agent)

        response = self.client.get(
            self.detail_url(ticket_without_comments),
        )

        self.assertContains(
            response,
            "No comments or internal notes have been added.",
        )
