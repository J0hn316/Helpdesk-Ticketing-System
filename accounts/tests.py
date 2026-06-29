from django.urls import reverse
from django.test import TestCase
from django.contrib.auth import get_user_model

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


class AuthenticationViewTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            username="john",
            password="testpass123",
            role=User.Role.REQUESTER,
        )

    def test_login_page_is_available(self) -> None:
        response = self.client.get(
            reverse("accounts:login"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "registration/login.html",
        )
        self.assertContains(response, "Log in")

    def test_user_can_log_in(self) -> None:
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "john",
                "password": "testpass123",
            },
        )

        self.assertRedirects(
            response,
            reverse("dashboard:home"),
        )

        self.assertEqual(
            int(self.client.session["_auth_user_id"]),
            self.user.pk,
        )

    def test_invalid_credentials_do_not_log_user_in(self) -> None:
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "john",
                "password": "incorrect-password",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Your username or password was incorrect.",
        )
        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_authenticated_user_is_redirected_from_login_page(
        self,
    ) -> None:
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("accounts:login"),
        )

        self.assertRedirects(
            response,
            reverse("dashboard:home"),
        )

    def test_user_can_log_out_with_post_request(self) -> None:
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("accounts:logout"),
        )

        self.assertRedirects(
            response,
            reverse("accounts:login"),
        )
        self.assertNotIn(
            "_auth_user_id",
            self.client.session,
        )

    def test_logout_does_not_accept_get_request(self) -> None:
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("accounts:logout"),
        )

        self.assertEqual(response.status_code, 405)
        self.assertIn(
            "_auth_user_id",
            self.client.session,
        )


class RegistrationViewTests(TestCase):
    def valid_registration_data(self) -> dict[str, str]:
        return {
            "username": "newrequester",
            "email": "requester@example.com",
            "first_name": "New",
            "last_name": "Requester",
            "password1": "SecureTestPass123!",
            "password2": "SecureTestPass123!",
        }

    def test_registration_page_is_available(self) -> None:
        response = self.client.get(
            reverse("accounts:register"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "accounts/register.html",
        )
        self.assertContains(
            response,
            "Create a requester account",
        )

    def test_valid_registration_creates_requester(self) -> None:
        response = self.client.post(
            reverse("accounts:register"),
            self.valid_registration_data(),
        )

        user = User.objects.get(
            username="newrequester",
        )

        self.assertEqual(
            user.role,
            User.Role.REQUESTER,
        )
        self.assertEqual(
            user.email,
            "requester@example.com",
        )
        self.assertTrue(
            user.check_password("SecureTestPass123!"),
        )
        self.assertRedirects(
            response,
            reverse("dashboard:home"),
        )

    def test_registered_user_is_logged_in(self) -> None:
        self.client.post(
            reverse("accounts:register"),
            self.valid_registration_data(),
        )

        user = User.objects.get(
            username="newrequester",
        )

        self.assertEqual(
            int(self.client.session["_auth_user_id"]),
            user.pk,
        )

    def test_registration_form_does_not_contain_role_field(
        self,
    ) -> None:
        response = self.client.get(
            reverse("accounts:register"),
        )

        self.assertNotIn(
            "role",
            response.context["form"].fields,
        )

    def test_registration_ignores_submitted_admin_role(
        self,
    ) -> None:
        registration_data = self.valid_registration_data()
        registration_data["role"] = User.Role.ADMIN

        self.client.post(
            reverse("accounts:register"),
            registration_data,
        )

        user = User.objects.get(
            username="newrequester",
        )

        self.assertEqual(
            user.role,
            User.Role.REQUESTER,
        )

    def test_mismatched_passwords_do_not_create_user(self) -> None:
        registration_data = self.valid_registration_data()
        registration_data["password2"] = "DifferentPassword123!"

        response = self.client.post(
            reverse("accounts:register"),
            registration_data,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            User.objects.filter(
                username="newrequester",
            ).exists()
        )
        self.assertContains(
            response,
            "The two password fields didn’t match.",
        )

    def test_duplicate_username_does_not_create_user(self) -> None:
        User.objects.create_user(
            username="newrequester",
            password="ExistingPass123!",
        )

        response = self.client.post(
            reverse("accounts:register"),
            self.valid_registration_data(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            User.objects.filter(
                username="newrequester",
            ).count(),
            1,
        )

    def test_authenticated_user_is_redirected_from_registration(
        self,
    ) -> None:
        user = User.objects.create_user(
            username="existinguser",
            password="testpass123",
        )
        self.client.force_login(user)

        response = self.client.get(
            reverse("accounts:register"),
        )

        self.assertRedirects(
            response,
            reverse("dashboard:home"),
        )
