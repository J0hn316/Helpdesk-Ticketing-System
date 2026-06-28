from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class UserModelTests(TestCase):
    def test_new_user_defaults_to_requester_role(self) -> None:
        user = User.objects.create_user(
            username="john",
            password="testpass123",
        )

        self.assertEqual(user.role, User.Role.REQUESTER)
        self.assertTrue(user.is_requester)
        self.assertFalse(user.is_agent)
        self.assertFalse(user.is_helpdesk_admin)

    def test_user_can_be_created_as_agent(self) -> None:
        user = User.objects.create_user(
            username="agent",
            password="testpass123",
            role=User.Role.AGENT,
        )

        self.assertEqual(user.role, User.Role.AGENT)
        self.assertTrue(user.is_agent)
        self.assertFalse(user.is_requester)
        self.assertFalse(user.is_helpdesk_admin)

    def test_user_can_be_created_as_helpdesk_admin(self) -> None:
        user = User.objects.create_user(
            username="helpdeskadmin",
            password="testpass123",
            role=User.Role.ADMIN,
        )

        self.assertEqual(user.role, User.Role.ADMIN)
        self.assertTrue(user.is_helpdesk_admin)
        self.assertFalse(user.is_requester)
        self.assertFalse(user.is_agent)

    def test_user_string_representation_is_username(self) -> None:
        user = User.objects.create_user(
            username="john",
            password="testpass123",
        )

        self.assertEqual(str(user), "john")

    def test_create_user_hashes_password(self) -> None:
        user = User.objects.create_user(
            username="john",
            password="testpass123",
        )

        self.assertNotEqual(user.password, "testpass123")
        self.assertTrue(user.check_password("testpass123"))
