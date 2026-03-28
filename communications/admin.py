from django.contrib import admin

from .models import (
    ConversationMessage,
    ConversationThread,
    MessageImageAttachment,
    Notification,
)


class MessageImageAttachmentInline(admin.TabularInline):
    model = MessageImageAttachment
    extra = 0


@admin.register(ConversationThread)
class ConversationThreadAdmin(admin.ModelAdmin):
    list_display = (
        "subject_text",
        "farmer",
        "provider_name_snapshot",
        "status",
        "assigned_veterinary_user",
        "last_message_at",
    )
    list_filter = ("status", "provider_service_type")
    search_fields = (
        "subject",
        "provider_name_snapshot",
        "farmer__username",
        "farmer__first_name",
        "farmer__last_name",
    )


@admin.register(ConversationMessage)
class ConversationMessageAdmin(admin.ModelAdmin):
    list_display = ("thread", "sender", "sender_role_snapshot", "created_at", "read_at")
    list_filter = ("sender_role_snapshot",)
    search_fields = ("body", "sender__username")
    inlines = [MessageImageAttachmentInline]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "recipient", "notification_type", "created_at", "read_at")
    list_filter = ("notification_type",)
    search_fields = ("title", "body", "recipient__username")

