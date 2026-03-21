from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class CoreWebHomeTests(TestCase):
    def test_home_page_loads(self):
        response = self.client.get(reverse("Core_Web:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CowCalving")
        self.assertContains(response, "Shared website")
        self.assertContains(response, "/accounts/login/")

    def test_home_page_shows_profile_link_for_authenticated_user_without_role(self):
        user = User.objects.create_user(
            username="home-user",
            email="home@example.com",
            password="StrongPass123!",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("Core_Web:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Complete Your Profile")
        self.assertContains(response, "/dashboard/profile/")

    def test_home_page_shows_role_dashboard_action_for_authenticated_user(self):
        from users.models import Profile, Role

        user = User.objects.create_user(
            username="home-role-user",
            email="home-role@example.com",
            password="StrongPass123!",
        )
        role, _ = Role.objects.get_or_create(
            slug="farmer",
            defaults={
                "name": "Farmer",
                "dashboard_namespace": "farmers_dashboard",
                "default_path": "/farmers/",
            },
        )
        Profile.objects.create(user=user, role=role)
        self.client.force_login(user)

        response = self.client.get(reverse("Core_Web:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Open Farmer Dashboard")
        self.assertContains(response, "/farmers/")
