import re
from django.test import TestCase
from django.urls import resolve
from django.urls import reverse
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMultiAlternatives
from django.core import mail
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import override_settings

from cow_calving_MAIN.context_processors import dev_static_version

from .email_backends import BrevoAPIEmailBackend
from .forms import CowCalvingRegisterForm
from users.models import Profile, Role


class AccountsViewTests(TestCase):
    def setUp(self):
        self.farmer_role, _ = Role.objects.get_or_create(
            slug="farmer",
            defaults={
                "name": "Farmer",
                "post_login_path": "/",
                "dashboard_namespace": "farmers_dashboard",
                "default_path": "/farmers/",
            },
        )
        self.veterinary_role, _ = Role.objects.get_or_create(
            slug="veterinary",
            defaults={
                "name": "Veterinary",
                "post_login_path": "/veterinary/",
                "dashboard_namespace": "veterinary_dashboard",
                "default_path": "/veterinary/",
            },
        )

    def test_login_page_loads(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Continue with Google")
        self.assertContains(response, 'formaction="/accounts/google/login/"')
        self.assertContains(response, "Choose your account type to continue securely.")
        self.assertContains(response, "Email")
        self.assertContains(response, "Professional ID")
        self.assertContains(response, "accounts/feedback.js")
        self.assertContains(response, "Reimagining Dairy Farming")

    def test_register_page_loads(self):
        response = self.client.get(reverse("accounts:signup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Set up your CowCalving farmer profile.")
        self.assertContains(response, "First Name")
        self.assertContains(response, "Last Name")
        self.assertContains(response, "Username")
        self.assertContains(response, "Farm Name")
        self.assertContains(response, "This registration page is for farmers only.")

    def test_login_page_logs_out_authenticated_user(self):
        user = User.objects.create_user(
            username="signed-in-user",
            email="signedin@example.com",
            password="StrongPass123!",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("accounts:login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please sign in again to continue.")
        self.assertContains(response, "data-auto-dismiss-message")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_register_page_logs_out_authenticated_user(self):
        user = User.objects.create_user(
            username="signed-in-user-2",
            email="signedin2@example.com",
            password="StrongPass123!",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("accounts:signup"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your previous session was closed. Create or sign in again.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_google_login_route_exists(self):
        match = resolve("/accounts/google/login/")
        self.assertEqual(match.view_name, "google_login")

    def test_password_reset_page_loads(self):
        response = self.client.get("/accounts/password/reset/")
        self.assertEqual(response.status_code, 200)

    def test_password_reset_done_page_loads(self):
        response = self.client.get("/accounts/password/reset/done/")
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("accounts:password_reset_request"))

    def test_password_reset_verify_requires_code_session(self):
        response = self.client.get("/accounts/password/reset/verify/")
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("accounts:password_reset_request"))

    def test_csrf_failure_uses_friendly_page(self):
        client = self.client_class(enforce_csrf_checks=True)
        response = client.post(
            reverse("accounts:login"),
            {"username": "wrong", "password": "wrong"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "This page expired", status_code=403)
        self.assertContains(response, "Back to Sign In", status_code=403)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_register_redirects_to_verification_page_when_email_verification_is_mandatory(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "first_name": "Kelvin",
                "last_name": "Muriuki",
                "username": "kelvin",
                "email": "kelvin@example.com",
                "farm_name": "Demo Farm",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
            follow=False,
        )

        self.assertRedirects(
            response,
            reverse("account_email_verification_sent"),
            fetch_redirect_response=False,
        )
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any("Check your email to verify your account" in str(message) for message in messages)
        )

    @override_settings(ACCOUNT_EMAIL_VERIFICATION="none")
    def test_register_creates_farmer_profile_and_redirects_to_home_page(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "first_name": "Kelvin",
                "last_name": "Muriuki",
                "username": "kelvin-profile",
                "email": "kelvin-profile@example.com",
                "farm_name": "Demo Farm",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
            follow=False,
        )

        self.assertRedirects(response, "/", fetch_redirect_response=False)
        user = User.objects.get(username="kelvin-profile")
        profile = Profile.objects.get(user=user)
        self.assertEqual(profile.role, self.farmer_role)
        self.assertEqual(profile.farm_name, "Demo Farm")

    def test_farmer_login_redirects_to_home_page(self):
        user = User.objects.create_user(
            username="login-home-user",
            email="login-home@example.com",
            password="StrongPass123!",
        )
        Profile.objects.create(user=user, role=self.farmer_role)

        response = self.client.post(
            reverse("accounts:login"),
            {
                "login_type": "farmer",
                "email": "login-home@example.com",
                "password": "StrongPass123!",
            },
            follow=False,
        )

        self.assertRedirects(response, "/", fetch_redirect_response=False)

    def test_veterinary_login_redirects_to_home_page(self):
        user = User.objects.create_user(
            username="vet-login-user",
            email="vet-login@example.com",
            password="StrongPass123!",
        )
        Profile.objects.create(
            user=user,
            role=self.veterinary_role,
            professional_id="VET-204",
        )

        response = self.client.post(
            reverse("accounts:login"),
            {
                "login_type": "veterinary",
                "professional_id": "vet-204",
                "password": "StrongPass123!",
            },
            follow=False,
        )

        self.assertRedirects(response, "/", fetch_redirect_response=False)

    def test_veterinary_account_cannot_sign_in_through_farmer_login_path(self):
        user = User.objects.create_user(
            username="vet-username-user",
            email="vet-username@example.com",
            password="StrongPass123!",
        )
        Profile.objects.create(
            user=user,
            role=self.veterinary_role,
            professional_id="VET-205",
        )

        response = self.client.post(
            reverse("accounts:login"),
            {
                "login_type": "farmer",
                "email": "vet-username@example.com",
                "password": "StrongPass123!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Veterinary accounts must sign in with the professional ID assigned by admin.",
        )

    def test_superuser_can_sign_in_through_farmer_login_path(self):
        user = User.objects.create_superuser(
            username="admin-farmer-login",
            email="admin-farmer@example.com",
            password="StrongPass123!",
        )
        Profile.objects.create(user=user, role=self.veterinary_role, professional_id="VET-900")

        response = self.client.post(
            reverse("accounts:login"),
            {
                "login_type": "farmer",
                "email": "admin-farmer@example.com",
                "password": "StrongPass123!",
            },
            follow=False,
        )

        self.assertRedirects(response, "/", fetch_redirect_response=False)

    def test_superuser_can_sign_in_through_veterinary_login_path(self):
        user = User.objects.create_superuser(
            username="admin-vet-login",
            email="admin-vet@example.com",
            password="StrongPass123!",
        )
        Profile.objects.create(user=user, role=self.farmer_role, professional_id="VET-901")

        response = self.client.post(
            reverse("accounts:login"),
            {
                "login_type": "veterinary",
                "professional_id": "VET-901",
                "password": "StrongPass123!",
            },
            follow=False,
        )

        self.assertRedirects(response, "/", fetch_redirect_response=False)


class CowCalvingRegisterFormTests(TestCase):
    def setUp(self):
        self.farmer_role, _ = Role.objects.get_or_create(
            slug="farmer",
            defaults={
                "name": "Farmer",
                "post_login_path": "/",
                "dashboard_namespace": "farmers_dashboard",
                "default_path": "/farmers/",
            },
        )
        self.veterinary_role, _ = Role.objects.get_or_create(
            slug="veterinary",
            defaults={
                "name": "Veterinary",
                "post_login_path": "/veterinary/",
                "dashboard_namespace": "veterinary_dashboard",
                "default_path": "/veterinary/",
            },
        )

    def test_register_form_rejects_duplicate_email(self):
        first_form = CowCalvingRegisterForm(
            data={
                "first_name": "Amina",
                "last_name": "Njeri",
                "username": "amina",
                "email": "dupe@example.com",
                "farm_name": "North Farm",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            }
        )
        self.assertTrue(first_form.is_valid(), first_form.errors)
        first_form.save()

        second_form = CowCalvingRegisterForm(
            data={
                "first_name": "Faith",
                "last_name": "Wambui",
                "username": "faith",
                "email": "dupe@example.com",
                "farm_name": "South Farm",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            }
        )

        self.assertFalse(second_form.is_valid())
        self.assertIn("email", second_form.errors)

    def test_register_form_is_farmer_only(self):
        form = CowCalvingRegisterForm()

        self.assertNotIn("role", form.fields)


class DevStaticVersionTests(TestCase):
    @override_settings(DEBUG=True)
    def test_dev_static_version_changes_in_debug(self):
        payload = dev_static_version(request=None)
        self.assertTrue(payload["dev_static_version"].isdigit())

    @override_settings(DEBUG=False)
    def test_dev_static_version_disabled_outside_debug(self):
        payload = dev_static_version(request=None)
        self.assertEqual(payload["dev_static_version"], "")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PasswordResetCodeFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="reset-user",
            email="reset@example.com",
            password="OldStrongPass123!",
        )

    def test_password_reset_request_sends_code_and_redirects(self):
        response = self.client.post(
            reverse("accounts:password_reset_request"),
            {"email": self.user.email},
        )

        self.assertRedirects(response, reverse("accounts:password_reset_verify"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("reset your password", mail.outbox[0].body)
        self.assertRegex(mail.outbox[0].body, r"\b\d{6}\b")

        session = self.client.session
        self.assertIn("password_reset_code_state", session)
        self.assertEqual(
            session["password_reset_code_state"]["email"],
            self.user.email,
        )

    def test_password_reset_verify_updates_password(self):
        self.client.post(
            reverse("accounts:password_reset_request"),
            {"email": self.user.email},
        )
        match = re.search(r"(\d{6})", mail.outbox[0].body)
        self.assertIsNotNone(match)
        code = match.group(1)

        response = self.client.post(
            reverse("accounts:password_reset_verify"),
            {
                "code": code,
                "new_password1": "NewStrongPass123!",
                "new_password2": "NewStrongPass123!",
            },
        )

        self.assertRedirects(response, reverse("accounts:login"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewStrongPass123!"))
        self.assertNotIn("password_reset_code_state", self.client.session)

    def test_password_reset_verify_rejects_wrong_code(self):
        self.client.post(
            reverse("accounts:password_reset_request"),
            {"email": self.user.email},
        )

        response = self.client.post(
            reverse("accounts:password_reset_verify"),
            {
                "code": "000000",
                "new_password1": "NewStrongPass123!",
                "new_password2": "NewStrongPass123!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "That reset code is not valid.")

    def test_password_reset_done_redirects_to_verify_when_code_session_exists(self):
        self.client.post(
            reverse("accounts:password_reset_request"),
            {"email": self.user.email},
        )

        response = self.client.get(reverse("accounts:password_reset_done"))

        self.assertRedirects(response, reverse("accounts:password_reset_verify"))

    def test_password_reset_request_supports_social_only_account(self):
        social_user = User.objects.create_user(
            username="social-user",
            email="social@example.com",
        )
        social_user.set_unusable_password()
        social_user.save()

        response = self.client.post(
            reverse("accounts:password_reset_request"),
            {"email": social_user.email},
        )

        self.assertRedirects(response, reverse("accounts:password_reset_verify"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertRegex(mail.outbox[0].body, r"\b\d{6}\b")

    def test_password_reset_request_shows_error_for_unknown_email(self):
        response = self.client.post(
            reverse("accounts:password_reset_request"),
            {"email": "missing@example.com"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "We could not find an active account with that email.")
        self.assertNotIn("password_reset_code_state", self.client.session)

    @patch("accounts.views._send_password_reset_code")
    def test_password_reset_request_shows_error_when_email_send_fails(self, mocked_send):
        mocked_send.side_effect = RuntimeError("mail failed")

        response = self.client.post(
            reverse("accounts:password_reset_request"),
            {"email": self.user.email},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "We could not send the reset code right now.")
        self.assertNotIn("password_reset_code_state", self.client.session)


class BrevoAPIEmailBackendTests(TestCase):
    @override_settings(BREVO_API_KEY="")
    def test_backend_requires_api_key(self):
        backend = BrevoAPIEmailBackend(fail_silently=False)
        message = EmailMultiAlternatives(
            subject="Verify your account",
            body="Plain text body",
            from_email="Farm App <no-reply@example.com>",
            to=["farmer@example.com"],
        )

        with self.assertRaises(ImproperlyConfigured):
            backend.send_messages([message])

    @override_settings(
        BREVO_API_KEY="test-key",
        BREVO_SENDER_NAME="Cow Calving",
    )
    @patch("accounts.email_backends.requests.post")
    def test_backend_sends_html_and_text_payload(self, mocked_post):
        mocked_post.return_value.raise_for_status.return_value = None

        backend = BrevoAPIEmailBackend()
        message = EmailMultiAlternatives(
            subject="Verify your account",
            body="Plain text body",
            from_email="no-reply@example.com",
            to=["Farmer <farmer@example.com>"],
            cc=["vet@example.com"],
            bcc=["manager@example.com"],
            reply_to=["Support <support@example.com>"],
        )
        message.attach_alternative("<p>HTML body</p>", "text/html")

        sent_count = backend.send_messages([message])

        self.assertEqual(sent_count, 1)
        mocked_post.assert_called_once()
        _, kwargs = mocked_post.call_args
        self.assertEqual(kwargs["headers"]["api-key"], "test-key")
        self.assertEqual(kwargs["json"]["sender"]["email"], "no-reply@example.com")
        self.assertEqual(kwargs["json"]["sender"]["name"], "Cow Calving")
        self.assertEqual(kwargs["json"]["to"][0]["email"], "farmer@example.com")
        self.assertEqual(kwargs["json"]["cc"][0]["email"], "vet@example.com")
        self.assertEqual(kwargs["json"]["bcc"][0]["email"], "manager@example.com")
        self.assertEqual(kwargs["json"]["replyTo"]["email"], "support@example.com")
        self.assertEqual(kwargs["json"]["subject"], "Verify your account")
        self.assertEqual(kwargs["json"]["textContent"], "Plain text body")
        self.assertEqual(kwargs["json"]["htmlContent"], "<p>HTML body</p>")
