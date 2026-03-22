from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

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
        response = self.client.get(reverse("farmers_dashboard:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_farmer_dashboard_loads_for_farmer_role(self):
        Profile.objects.create(user=self.user, role=self.role)
        self.client.force_login(self.user)

        response = self.client.get(reverse("farmers_dashboard:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Farmer Control Room")
        self.assertContains(response, "The farmer dashboard map")
        self.assertContains(response, "Herd workspace")
        self.assertContains(response, "Alerts center")
        self.assertContains(response, "Reports and trends")
        self.assertContains(response, '<form method="post" action="/accounts/logout/">', html=False)
        self.assertNotContains(response, 'href="/accounts/logout/"', html=False)

    def test_farmer_detail_pages_load_for_farmer_role(self):
        Profile.objects.create(user=self.user, role=self.role)
        self.client.force_login(self.user)

        herd_response = self.client.get(reverse("farmers_dashboard:herd"))
        alerts_response = self.client.get(reverse("farmers_dashboard:alerts"))
        reports_response = self.client.get(reverse("farmers_dashboard:reports"))

        self.assertContains(herd_response, "Ready for real herd records")
        self.assertContains(alerts_response, "Professional alert cards with next actions")
        self.assertContains(reports_response, "Weekly production view")

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

        response = self.client.get(reverse("farmers_dashboard:dashboard"))

        self.assertRedirects(response, "/veterinary/", fetch_redirect_response=False)
