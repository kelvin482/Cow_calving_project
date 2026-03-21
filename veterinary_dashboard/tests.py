from django.contrib.auth.models import User
from django.test import TestCase

from users.models import Profile, Role


class VeterinaryDashboardViewTests(TestCase):
    def setUp(self):
        self.role, _ = Role.objects.get_or_create(
            slug="veterinary",
            defaults={
                "name": "Veterinary",
                "dashboard_namespace": "veterinary_dashboard",
                "default_path": "/veterinary/",
            },
        )
        self.user = User.objects.create_user(
            username="vet-user",
            email="vet@example.com",
            password="StrongPass123!",
        )

    def test_veterinary_dashboard_requires_login(self):
        response = self.client.get("/veterinary/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_veterinary_dashboard_loads_for_veterinary_role(self):
        Profile.objects.create(user=self.user, role=self.role)
        self.client.force_login(self.user)

        response = self.client.get("/veterinary/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Veterinary Dashboard")
        self.assertContains(response, "Open Menu")
        self.assertContains(response, "My Profile")
        self.assertContains(response, "AI Workspace")
        self.assertContains(response, '<form method="post" action="/accounts/logout/">', html=False)
        self.assertNotContains(response, 'href="/accounts/logout/"', html=False)

    def test_veterinary_dashboard_redirects_other_roles(self):
        other_role, _ = Role.objects.get_or_create(
            slug="farmer",
            defaults={
                "name": "Farmer",
                "dashboard_namespace": "farmers_dashboard",
                "default_path": "/farmers/",
            },
        )
        Profile.objects.create(user=self.user, role=other_role)
        self.client.force_login(self.user)

        response = self.client.get("/veterinary/")

        self.assertRedirects(response, "/farmers/", fetch_redirect_response=False)
