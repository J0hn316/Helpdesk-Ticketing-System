from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError

from .models import Category, Ticket

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
