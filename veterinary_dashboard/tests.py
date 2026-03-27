from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from communications.models import ConversationThread, Notification
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
        self.assertContains(response, "Overview")
        self.assertContains(response, "Active Case")
        self.assertContains(response, "Farm Map")
        self.assertContains(response, "Messages")
        self.assertContains(response, "My Farms")
        self.assertContains(response, "Medical Records")
        self.assertContains(response, "Notifications")
        self.assertContains(response, "Workspace")
        self.assertContains(response, "My Profile")
        self.assertContains(response, "AI Workspace")
        self.assertContains(response, "Sign out")
        self.assertContains(response, "Back to website")
        self.assertContains(response, "Logout")
        self.assertContains(response, "AI workspace")
        self.assertContains(response, 'data-dashboard-ai-resize-handle', html=False)
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
            reverse("veterinary_dashboard:farm_map"),
            reverse("veterinary_dashboard:messages"),
            reverse("veterinary_dashboard:medical_records"),
            reverse("veterinary_dashboard:notifications"),
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
                if route == reverse("veterinary_dashboard:messages"):
                    self.assertContains(response, "Messages")
                elif route == reverse("veterinary_dashboard:notifications"):
                    self.assertContains(response, "Notifications")
                else:
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
        self.assertContains(response, "Active case queue")
        self.assertContains(response, "Cases ready for action")
        self.assertContains(response, "Selected active case")
        self.assertContains(response, "Case health bar")
        self.assertContains(response, "Progress tracker")
        self.assertContains(response, "Keep the essentials open")
        self.assertContains(response, "Clinical snapshot")
        self.assertNotContains(response, "AI recommendation")
        self.assertNotContains(response, "Draft note for this case")
        self.assertContains(response, 'id="patient-list"', html=False)

    def test_veterinary_can_reply_to_farmer_thread_with_image(self):
        Profile.objects.create(user=self.user, role=self.role)
        farmer_role, _ = Role.objects.get_or_create(
            slug="farmer",
            defaults={
                "name": "Farmer",
                "dashboard_namespace": "farmers_dashboard",
                "default_path": "/farmers/",
            },
        )
        farmer = User.objects.create_user(
            username="farmer-thread",
            email="farmer-thread@example.com",
            password="StrongPass123!",
        )
        Profile.objects.create(user=farmer, role=farmer_role)
        thread = ConversationThread.objects.create(
            farmer=farmer,
            provider_key="veterinary-dr-james-mwangi",
            provider_name_snapshot="Dr. James Mwangi",
            provider_title_snapshot="Large animal veterinarian",
            provider_service_type="veterinary",
            subject="Help with labour signs",
        )
        thread.messages.create(
            thread=thread,
            sender=farmer,
            sender_role_snapshot="farmer",
            body="My cow has started labour and I need help.",
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("veterinary_dashboard:messages_thread", args=[thread.pk]),
            data={
                "body": "Keep the pen ready and share another update in one hour.",
                "image": SimpleUploadedFile(
                    "reply.png",
                    b"fake-image-content",
                    content_type="image/png",
                ),
            },
            follow=True,
        )

        thread.refresh_from_db()
        self.assertEqual(thread.assigned_veterinary_user, self.user)
        self.assertEqual(thread.messages.count(), 2)
        self.assertEqual(thread.messages.last().attachments.count(), 1)
        self.assertTrue(
            Notification.objects.filter(
                recipient=farmer,
                notification_type=Notification.TYPE_PROVIDER_REPLIED,
                thread=thread,
            ).exists()
        )
        self.assertContains(response, "Reply sent to the farmer.")

    def test_farm_map_uses_saved_farmer_locations(self):
        Profile.objects.create(user=self.user, role=self.role)
        farmer_role, _ = Role.objects.get_or_create(
            slug="farmer",
            defaults={
                "name": "Farmer",
                "dashboard_namespace": "farmers_dashboard",
                "default_path": "/farmers/",
            },
        )
        farmer = User.objects.create_user(
            username="mapped-farmer",
            email="mapped-farmer@example.com",
            password="StrongPass123!",
            first_name="Mary",
            last_name="Njeri",
        )
        farmer_profile = Profile.objects.create(
            user=farmer,
            role=farmer_role,
            farm_name="Sunrise Farm",
            phone_number="+254700111222",
            farm_latitude="-0.303100",
            farm_longitude="36.080000",
            farm_location_source="manual_pin",
        )
        _ = farmer_profile
        self.client.force_login(self.user)

        response = self.client.get(reverse("veterinary_dashboard:farm_map"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Saved farm locations")
        self.assertContains(response, "Sunrise Farm")
        self.assertContains(response, "Road route preview")
        self.assertContains(response, "Use my location")
        self.assertContains(response, "Preview route")
        self.assertContains(response, "Selected destination")
        self.assertContains(response, "Hover a farm card or marker")
        self.assertContains(response, "Unread farmer messages")
        self.assertContains(response, "Get directions")
        self.assertContains(
            response,
            "google.com/maps/dir/?api=1&amp;destination=-0.303100,36.080000",
        )
