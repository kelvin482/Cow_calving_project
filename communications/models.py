from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone


class ConversationThread(models.Model):
    STATUS_OPEN = "open"
    STATUS_WAITING_FOR_VET = "waiting_for_vet"
    STATUS_WAITING_FOR_FARMER = "waiting_for_farmer"
    STATUS_CLOSED = "closed"

    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_WAITING_FOR_VET, "Waiting for veterinary reply"),
        (STATUS_WAITING_FOR_FARMER, "Waiting for farmer reply"),
        (STATUS_CLOSED, "Closed"),
    ]

    farmer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversation_threads",
    )
    assigned_veterinary_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_conversation_threads",
    )
    provider_key = models.CharField(max_length=64, blank=True)
    provider_name_snapshot = models.CharField(max_length=120)
    provider_title_snapshot = models.CharField(max_length=120, blank=True)
    provider_service_type = models.CharField(max_length=32, blank=True)
    cow = models.ForeignKey(
        "farmers_dashboard.Cow",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversation_threads",
    )
    insemination_request = models.ForeignKey(
        "farmers_dashboard.InseminationRequest",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversation_threads",
    )
    subject = models.CharField(max_length=160, blank=True)
    status = models.CharField(
        max_length=24,
        choices=STATUS_CHOICES,
        default=STATUS_OPEN,
    )
    last_message_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_message_at", "-updated_at"]

    def __str__(self):
        return self.subject or f"Conversation with {self.provider_name_snapshot}"

    @property
    def subject_text(self):
        if self.subject:
            return self.subject
        if self.cow:
            return f"{self.cow.name} support"
        return f"Message for {self.provider_name_snapshot}"


class ConversationMessage(models.Model):
    thread = models.ForeignKey(
        ConversationThread,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversation_messages",
    )
    sender_role_snapshot = models.CharField(max_length=50, blank=True)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"Message in {self.thread_id} from {self.sender}"

    @property
    def is_read(self):
        return self.read_at is not None


class MessageImageAttachment(models.Model):
    message = models.ForeignKey(
        ConversationMessage,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    image = models.FileField(
        upload_to="message_attachments/%Y/%m/",
        validators=[
            FileExtensionValidator(
                allowed_extensions=["jpg", "jpeg", "png", "webp"]
            )
        ],
    )
    caption = models.CharField(max_length=160, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"Attachment for message {self.message_id}"


class Notification(models.Model):
    TYPE_NEW_FARMER_MESSAGE = "new_farmer_message"
    TYPE_PROVIDER_REPLIED = "provider_replied"

    TYPE_CHOICES = [
        (TYPE_NEW_FARMER_MESSAGE, "New farmer message"),
        (TYPE_PROVIDER_REPLIED, "Provider replied"),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notification_actions",
    )
    notification_type = models.CharField(max_length=40, choices=TYPE_CHOICES)
    title = models.CharField(max_length=140)
    body = models.CharField(max_length=255)
    action_url = models.CharField(max_length=255, blank=True)
    thread = models.ForeignKey(
        ConversationThread,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    cow = models.ForeignKey(
        "farmers_dashboard.Cow",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    insemination_request = models.ForeignKey(
        "farmers_dashboard.InseminationRequest",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.title

    @property
    def is_read(self):
        return self.read_at is not None

