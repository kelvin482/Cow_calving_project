from email.utils import parseaddr

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.base import BaseEmailBackend


class BrevoAPIEmailBackend(BaseEmailBackend):
    """
    Send transactional email through Brevo's HTTP API.

    This backend is useful when you have a Brevo API key instead of SMTP
    credentials. It supports standard Django EmailMessage objects used by
    django-allauth for verification and password reset emails.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_key = getattr(settings, "BREVO_API_KEY", "").strip()
        self.api_url = getattr(
            settings, "BREVO_API_URL", "https://api.brevo.com/v3/smtp/email"
        ).strip()
        self.timeout = int(getattr(settings, "BREVO_API_TIMEOUT", 15))
        self.default_sender_name = getattr(settings, "BREVO_SENDER_NAME", "").strip()
        self.sandbox_mode = bool(getattr(settings, "BREVO_SANDBOX_MODE", False))

    def _split_address(self, address):
        name, email = parseaddr(address or "")
        return name.strip(), email.strip()

    def _format_address(self, address):
        # Brevo expects structured sender/recipient objects rather than raw RFC strings.
        name, email = self._split_address(address)
        if not email:
            return None
        payload = {"email": email}
        if name:
            payload["name"] = name
        return payload

    def _get_sender(self, message):
        sender = self._format_address(message.from_email or settings.DEFAULT_FROM_EMAIL)
        if not sender:
            raise ImproperlyConfigured("Set DEFAULT_FROM_EMAIL to a valid sender address.")
        if self.default_sender_name and "name" not in sender:
            sender["name"] = self.default_sender_name
        return sender

    def _get_content_payload(self, message):
        payload = {}
        if getattr(message, "content_subtype", "plain") == "html":
            payload["htmlContent"] = message.body
        else:
            payload["textContent"] = message.body

        # Prefer any HTML alternative so styled templates render properly in mail clients.
        for alternative, mimetype in getattr(message, "alternatives", []):
            if mimetype == "text/html":
                payload["htmlContent"] = alternative
        return payload

    def _build_payload(self, message):
        # Build the API payload from Django's EmailMessage shape in one place.
        payload = {
            "sender": self._get_sender(message),
            "to": [
                recipient
                for recipient in (self._format_address(addr) for addr in message.to)
                if recipient
            ],
            "subject": message.subject,
            **self._get_content_payload(message),
        }

        cc = [
            recipient
            for recipient in (self._format_address(addr) for addr in message.cc)
            if recipient
        ]
        if cc:
            payload["cc"] = cc

        bcc = [
            recipient
            for recipient in (self._format_address(addr) for addr in message.bcc)
            if recipient
        ]
        if bcc:
            payload["bcc"] = bcc

        reply_to = getattr(message, "reply_to", None) or []
        if reply_to:
            reply_to_payload = self._format_address(reply_to[0])
            if reply_to_payload:
                payload["replyTo"] = reply_to_payload

        if self.sandbox_mode:
            # Brevo sandbox mode accepts the request without delivering a real email.
            payload["headers"] = {"X-Sib-Sandbox": "drop"}

        return payload

    def _build_api_error(self, response):
        """Keep Brevo's rejection reason while avoiding request-header secrets."""
        try:
            response_data = response.json()
        except ValueError:
            response_data = {}
        if not isinstance(response_data, dict):
            response_data = {}

        error_code = response_data.get("code")
        error_message = response_data.get("message") or "Brevo rejected the email request."
        detail = f" ({error_code})" if error_code else ""
        detail += f": {str(error_message)[:500]}"
        return requests.HTTPError(
            f"Brevo email request failed with HTTP {response.status_code}{detail}",
            response=response,
        )

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        if not self.api_key:
            if self.fail_silently:
                return 0
            raise ImproperlyConfigured(
                "Set BREVO_API_KEY to use accounts.email_backends.BrevoAPIEmailBackend."
            )

        sent_count = 0
        headers = {
            "accept": "application/json",
            "api-key": self.api_key,
            "content-type": "application/json",
        }

        for message in email_messages:
            try:
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=self._build_payload(message),
                    timeout=self.timeout,
                )
                if response.status_code >= 400:
                    raise self._build_api_error(response)
            except Exception:
                if not self.fail_silently:
                    raise
            else:
                sent_count += 1

        return sent_count


class ResendAPIEmailBackend(BaseEmailBackend):
    """Send standard Django email messages through the Resend REST API."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_key = getattr(settings, "RESEND_API_KEY", "").strip()
        self.api_url = getattr(
            settings, "RESEND_API_URL", "https://api.resend.com/emails"
        ).strip()
        self.timeout = int(getattr(settings, "RESEND_API_TIMEOUT", 15))

    def _build_payload(self, message):
        payload = {
            "from": message.from_email or settings.DEFAULT_FROM_EMAIL,
            "to": message.to,
            "subject": message.subject,
        }

        if getattr(message, "content_subtype", "plain") == "html":
            payload["html"] = message.body
        else:
            payload["text"] = message.body

        for alternative, mimetype in getattr(message, "alternatives", []):
            if mimetype == "text/html":
                payload["html"] = alternative

        if message.cc:
            payload["cc"] = message.cc
        if message.bcc:
            payload["bcc"] = message.bcc
        if message.reply_to:
            payload["reply_to"] = message.reply_to[0]

        return payload

    def _build_api_error(self, response):
        """Keep Resend's useful rejection detail while never exposing request headers."""
        try:
            response_data = response.json()
        except ValueError:
            response_data = {}
        if not isinstance(response_data, dict):
            response_data = {}

        error_data = response_data.get("error", response_data)
        if not isinstance(error_data, dict):
            error_data = {}

        error_code = error_data.get("name") or error_data.get("code")
        error_message = error_data.get("message") or "Resend rejected the email request."
        detail = f" ({error_code})" if error_code else ""
        detail += f": {str(error_message)[:500]}"
        return requests.HTTPError(
            f"Resend email request failed with HTTP {response.status_code}{detail}",
            response=response,
        )

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        if not self.api_key:
            if self.fail_silently:
                return 0
            raise ImproperlyConfigured(
                "Set RESEND_API_KEY to use accounts.email_backends.ResendAPIEmailBackend."
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        sent_count = 0
        for message in email_messages:
            try:
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=self._build_payload(message),
                    timeout=self.timeout,
                )
                if response.status_code >= 400:
                    raise self._build_api_error(response)
            except Exception:
                if not self.fail_silently:
                    raise
            else:
                sent_count += 1

        return sent_count
