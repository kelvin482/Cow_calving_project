from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from farmers_dashboard.forms import ServiceProviderMessageForm

from .forms import ConversationReplyForm


class UploadValidationTests(SimpleTestCase):
    def test_conversation_reply_rejects_non_image_content_type(self):
        upload = SimpleUploadedFile(
            "reply.png",
            b"fake-image-bytes",
            content_type="text/plain",
        )

        form = ConversationReplyForm(
            data={"body": "Please review this case."},
            files={"image": upload},
        )

        self.assertFalse(form.is_valid())
        self.assertIn("Upload an image file only.", form.errors["image"])

    def test_service_provider_message_rejects_large_image(self):
        upload = SimpleUploadedFile(
            "cow.png",
            b"a" * (5 * 1024 * 1024 + 1),
            content_type="image/png",
        )

        form = ServiceProviderMessageForm(
            data={
                "provider_key": "vet-demo",
                "message": "Please help with this cow today.",
            },
            files={"image": upload},
        )

        self.assertFalse(form.is_valid())
        self.assertIn("Image size should be 5 MB or less.", form.errors["image"])
