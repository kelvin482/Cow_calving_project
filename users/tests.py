from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .forms import ProfileUpdateForm
from .models import Profile, Role
from .services import (
    get_dashboard_url_for_user,
    get_or_create_profile,
    get_post_login_url_for_user,
)


class RoleModelTests(TestCase):
    def test_role_string_representation_uses_name(self):
        role, _ = Role.objects.get_or_create(
            slug="farmer",
            defaults={
                "name": "Farmer",
                "dashboard_namespace": "farmers_dashboard",
                "default_path": "/farmers/",
            },
        )
        self.assertEqual(str(role), "Farmer")


class ProfileServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="profile-user",
            email="profile@example.com",
            password="StrongPass123!",
        )

    def test_get_or_create_profile_creates_missing_profile(self):
        profile = get_or_create_profile(self.user)
        self.assertIsInstance(profile, Profile)
        self.assertEqual(profile.user, self.user)

    def test_dashboard_url_uses_role_default_path(self):
        role, _ = Role.objects.get_or_create(
            slug="farmer",
            defaults={
                "name": "Farmer",
                "post_login_path": "/",
                "dashboard_namespace": "farmers_dashboard",
                "default_path": "/farmers/",
            },
        )
        profile = get_or_create_profile(self.user)
        profile.role = role
        profile.save(update_fields=["role"])

        self.assertEqual(get_dashboard_url_for_user(self.user), "/farmers/")

    def test_dashboard_url_falls_back_when_role_missing(self):
        self.assertEqual(get_dashboard_url_for_user(self.user), "/dashboard/profile/")

    def test_post_login_url_uses_role_post_login_path(self):
        role, _ = Role.objects.get_or_create(
            slug="farmer",
            defaults={
                "name": "Farmer",
                "post_login_path": "/",
                "dashboard_namespace": "farmers_dashboard",
                "default_path": "/farmers/",
            },
        )
        profile = get_or_create_profile(self.user)
        profile.role = role
        profile.save(update_fields=["role"])

        self.assertEqual(get_post_login_url_for_user(self.user), "/")


class DashboardRedirectTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="redirect-user",
            email="redirect@example.com",
            password="StrongPass123!",
        )

    def test_dashboard_redirect_requires_login(self):
        response = self.client.get(reverse("users:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_dashboard_redirect_sends_role_user_to_dashboard(self):
        role, _ = Role.objects.get_or_create(
            slug="veterinary",
            defaults={
                "name": "Veterinary",
                "post_login_path": "/veterinary/",
                "dashboard_namespace": "veterinary_dashboard",
                "default_path": "/veterinary/",
            },
        )
        Profile.objects.create(user=self.user, role=role)
        self.client.force_login(self.user)

        response = self.client.get(reverse("users:dashboard"))

        self.assertRedirects(response, "/veterinary/", fetch_redirect_response=False)

    def test_dashboard_redirect_sends_farmer_to_home_page(self):
        role, _ = Role.objects.get_or_create(
            slug="farmer",
            defaults={
                "name": "Farmer",
                "post_login_path": "/",
                "dashboard_namespace": "farmers_dashboard",
                "default_path": "/farmers/",
            },
        )
        Profile.objects.create(user=self.user, role=role)
        self.client.force_login(self.user)

        response = self.client.get(reverse("users:dashboard"))

        self.assertRedirects(response, "/", fetch_redirect_response=False)

    def test_dashboard_redirect_falls_back_for_existing_users_without_role(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("users:dashboard"))

        self.assertRedirects(response, "/dashboard/profile/", fetch_redirect_response=False)


class ProfileUpdateFormTests(TestCase):
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
            username="profile-form-user",
            email="profile-form@example.com",
            password="StrongPass123!",
            first_name="Old",
            last_name="Name",
        )
        self.profile = get_or_create_profile(self.user)

    def test_profile_form_updates_user_and_profile_fields(self):
        form = ProfileUpdateForm(
            data={
                "first_name": "Kelvin",
                "last_name": "Muriuki",
                "email": "kelvin@example.com",
                "role": str(self.role.pk),
                "farm_name": "Sunrise Farm",
                "phone_number": "+254700000000",
            },
            user=self.user,
            profile=self.profile,
        )

        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        self.user.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.user.first_name, "Kelvin")
        self.assertEqual(self.profile.farm_name, "Sunrise Farm")
        self.assertTrue(self.profile.is_profile_complete)

    def test_profile_form_rejects_duplicate_email(self):
        User.objects.create_user(
            username="other-user",
            email="taken@example.com",
            password="StrongPass123!",
        )

        form = ProfileUpdateForm(
            data={
                "first_name": "Kelvin",
                "last_name": "Muriuki",
                "email": "taken@example.com",
                "role": str(self.role.pk),
                "farm_name": "Sunrise Farm",
                "phone_number": "",
            },
            user=self.user,
            profile=self.profile,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_profile_form_blocks_farmer_from_switching_to_veterinary(self):
        vet_role, _ = Role.objects.get_or_create(
            slug="veterinary",
            defaults={
                "name": "Veterinary",
                "post_login_path": "/veterinary/",
                "dashboard_namespace": "veterinary_dashboard",
                "default_path": "/veterinary/",
            },
        )

        form = ProfileUpdateForm(
            data={
                "first_name": "Kelvin",
                "last_name": "Muriuki",
                "email": "kelvin@example.com",
                "role": str(vet_role.pk),
                "farm_name": "Sunrise Farm",
                "phone_number": "",
            },
            user=self.user,
            profile=self.profile,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("role", form.errors)


class ProfileViewTests(TestCase):
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
            username="profile-view-user",
            email="profile-view@example.com",
            password="StrongPass123!",
            first_name="Amina",
            last_name="Njeri",
        )
        profile = get_or_create_profile(self.user)
        profile.role = self.role
        profile.farm_name = "Demo Farm"
        profile.phone_number = "+254711111111"
        profile.save()

    def test_profile_page_requires_login(self):
        response = self.client.get(reverse("users:profile"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_profile_page_loads(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("users:profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Profile details")
        self.assertContains(response, "Demo Farm")
        self.assertContains(response, "Veterinary")

    def test_profile_edit_updates_details(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("users:profile_edit"),
            {
                "first_name": "Faith",
                "last_name": "Wambui",
                "email": "updated@example.com",
                "role": str(self.role.pk),
                "farm_name": "Updated Farm",
                "phone_number": "+254722222222",
            },
            follow=False,
        )

        self.assertRedirects(response, reverse("users:profile"), fetch_redirect_response=False)
        self.user.refresh_from_db()
        profile = self.user.profile
        self.assertEqual(self.user.first_name, "Faith")
        self.assertEqual(self.user.email, "updated@example.com")
        self.assertEqual(profile.farm_name, "Updated Farm")

    def test_profile_edit_page_loads(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("users:profile_edit"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Save Profile")
