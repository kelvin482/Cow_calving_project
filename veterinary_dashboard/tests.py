from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

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
        self.assertContains(response, "Workspace")
        self.assertContains(response, "Dashboard")
        self.assertContains(response, "My Profile")
        self.assertContains(response, "AI Workspace")
        self.assertContains(response, "Sign out")
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

    def test_veterinary_workspace_pages_load_for_veterinary_role(self):
        Profile.objects.create(user=self.user, role=self.role)
        self.client.force_login(self.user)

        routes = [
            reverse("veterinary_dashboard:schedule"),
            reverse("veterinary_dashboard:farms"),
            reverse("veterinary_dashboard:patients"),
            reverse("veterinary_dashboard:diagnosis"),
            reverse("veterinary_dashboard:prescriptions"),
            reverse("veterinary_dashboard:labs"),
            reverse("veterinary_dashboard:telehealth"),
            reverse("veterinary_dashboard:analytics"),
        ]

        for route in routes:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Workspace")

    def test_schedule_page_uses_planner_layout(self):
        Profile.objects.create(user=self.user, role=self.role)
        self.client.force_login(self.user)

        response = self.client.get(reverse("veterinary_dashboard:schedule"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Schedule planner")
        self.assertContains(response, "Calendar and route view")
        self.assertContains(response, "Add visit to selected day")
        self.assertContains(response, 'id="agenda-list"', html=False)

    def test_patients_page_uses_case_list_layout(self):
        Profile.objects.create(user=self.user, role=self.role)
        self.client.force_login(self.user)

        response = self.client.get(reverse("veterinary_dashboard:patients"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Patient queue")
        self.assertContains(response, "Cases that need action")
        self.assertContains(response, "Selected case")
        self.assertContains(response, "Draft note for this case")
        self.assertContains(response, 'id="patient-list"', html=False)
