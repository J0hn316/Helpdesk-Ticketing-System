from django.urls import reverse
from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class DashboardViewTests(TestCase):
    def test_dashboard_requires_authentication(self) -> None:
        response = self.client.get(
            reverse("dashboard:home"),
        )

        expected_login_url = (
            f"{reverse('accounts:login')}" f"?next={reverse('dashboard:home')}"
        )

        self.assertRedirects(
            response,
            expected_login_url,
        )

    def test_requester_can_view_dashboard(self) -> None:
        requester = User.objects.create_user(
            username="requester",
            password="testpass123",
            role=User.Role.REQUESTER,
        )
        self.client.force_login(requester)

        response = self.client.get(
            reverse("dashboard:home"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "dashboard/home.html",
        )
        self.assertContains(
            response,
            "Requester workspace",
        )

    def test_agent_sees_agent_workspace(self) -> None:
        agent = User.objects.create_user(
            username="agent",
            password="testpass123",
            role=User.Role.AGENT,
        )
        self.client.force_login(agent)

        response = self.client.get(
            reverse("dashboard:home"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Support agent workspace",
        )
        self.assertNotContains(
            response,
            "Requester workspace",
        )

    def test_helpdesk_admin_sees_admin_workspace(self) -> None:
        helpdesk_admin = User.objects.create_user(
            username="helpdeskadmin",
            password="testpass123",
            role=User.Role.ADMIN,
        )
        self.client.force_login(helpdesk_admin)

        response = self.client.get(
            reverse("dashboard:home"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Helpdesk administration workspace",
        )

    def test_authenticated_navigation_contains_logout_form(
        self,
    ) -> None:
        requester = User.objects.create_user(
            username="requester",
            password="testpass123",
        )
        self.client.force_login(requester)

        response = self.client.get(
            reverse("dashboard:home"),
        )

        self.assertContains(
            response,
            reverse("accounts:logout"),
        )
        self.assertContains(
            response,
            'method="post"',
        )

    def test_anonymous_navigation_contains_authentication_links(
        self,
    ) -> None:
        response = self.client.get(
            reverse("accounts:login"),
        )

        self.assertContains(
            response,
            reverse("accounts:login"),
        )
        self.assertContains(
            response,
            reverse("accounts:register"),
        )
