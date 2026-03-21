from django.contrib.auth.models import User
from django.test import TestCase

from users.models import Profile, Role


class FarmersDashboardViewTests(TestCase):
    def setUp(self):
        self.role, _ = Role.objects.get_or_create(
            slug="farmer",
            defaults={
                "name": "Farmer",
                "dashboard_namespace": "farmers_dashboard",
                "default_path": "/farmers/",
            },
        )
        self.user = User.objects.create_user(
            username="farmer-user",
            email="farmer@example.com",
            password="StrongPass123!",
        )

    def test_farmer_dashboard_requires_login(self):
        response = self.client.get("/farmers/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_farmer_dashboard_loads_for_farmer_role(self):
        Profile.objects.create(user=self.user, role=self.role)
        self.client.force_login(self.user)

        response = self.client.get("/farmers/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Farmer Dashboard")
        self.assertContains(response, '<form method="post" action="/accounts/logout/">', html=False)
        self.assertNotContains(response, 'href="/accounts/logout/"', html=False)

    def test_farmer_dashboard_redirects_other_roles(self):
        other_role, _ = Role.objects.get_or_create(
            slug="veterinary",
            defaults={
                "name": "Veterinary",
                "dashboard_namespace": "veterinary_dashboard",
                "default_path": "/veterinary/",
            },
        )
        Profile.objects.create(user=self.user, role=other_role)
        self.client.force_login(self.user)

        response = self.client.get("/farmers/")

        self.assertRedirects(response, "/veterinary/", fetch_redirect_response=False)
