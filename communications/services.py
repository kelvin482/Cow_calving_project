from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Prefetch, Q
from django.urls import reverse
from django.utils import timezone

from .models import (
    ConversationMessage,
    ConversationThread,
    MessageImageAttachment,
    Notification,
)


ROLE_FARMER = "farmer"
ROLE_VETERINARY = "veterinary"


def get_role_slug_for_user(user):
    profile = getattr(user, "profile", None)
    if profile and profile.role:
        return profile.role.slug
    return ""


def is_veterinary_user(user):
    return get_role_slug_for_user(user) == ROLE_VETERINARY


def get_veterinary_users():
    user_model = get_user_model()
    return user_model.objects.filter(profile__role__slug=ROLE_VETERINARY).distinct()


def build_thread_action_url(user, thread):
    if is_veterinary_user(user):
        return reverse("veterinary_dashboard:messages_thread", args=[thread.pk])
    return reverse("farmers_dashboard:messages_thread", args=[thread.pk])


def get_threads_queryset_for_user(user):
    queryset = (
        ConversationThread.objects.select_related(
            "farmer",
            "assigned_veterinary_user",
            "cow",
            "insemination_request",
        )
        .prefetch_related(
            Prefetch(
                "messages",
                queryset=ConversationMessage.objects.select_related("sender")
                .prefetch_related("attachments")
                .order_by("created_at", "id"),
            )
        )
        .order_by("-last_message_at", "-updated_at")
    )
    if is_veterinary_user(user):
        return queryset.filter(
            Q(assigned_veterinary_user=user) | Q(assigned_veterinary_user__isnull=True)
        )
    return queryset.filter(farmer=user)


def get_thread_for_user(user, thread_id):
    return get_threads_queryset_for_user(user).filter(pk=thread_id).first()


def get_threads_for_user(user):
    threads = list(get_threads_queryset_for_user(user))
    for thread in threads:
        messages = list(thread.messages.all())
        latest_message = messages[-1] if messages else None
        thread.latest_message = latest_message
        thread.unread_message_count = sum(
            1
            for message in messages
            if message.read_at is None and message.sender_id != user.id
        )
    return threads


def get_unread_thread_count(user):
    queryset = ConversationMessage.objects.filter(read_at__isnull=True).exclude(sender=user)
    if is_veterinary_user(user):
        queryset = queryset.filter(
            Q(thread__assigned_veterinary_user=user)
            | Q(thread__assigned_veterinary_user__isnull=True)
        )
    else:
        queryset = queryset.filter(thread__farmer=user)
    return queryset.values("thread_id").distinct().count()


def get_notifications_for_user(user):
    return Notification.objects.select_related("thread", "cow", "actor").filter(
        recipient=user
    )


def get_unread_notification_count(user):
    return get_notifications_for_user(user).filter(read_at__isnull=True).count()


def mark_notification_read(notification, user):
    if notification.recipient_id != user.id or notification.read_at is not None:
        return
    notification.read_at = timezone.now()
    notification.save(update_fields=["read_at"])


def mark_thread_messages_read(thread, user):
    now = timezone.now()
    thread.messages.filter(read_at__isnull=True).exclude(sender=user).update(read_at=now)
    Notification.objects.filter(
        recipient=user,
        thread=thread,
        read_at__isnull=True,
    ).update(read_at=now)


def _build_thread_subject(provider, cow=None):
    if cow:
        return f"{cow.name} support request"
    provider_name = provider.get("name", "provider")
    return f"Message for {provider_name}"


def _build_notification_body(body):
    trimmed = " ".join((body or "").split())
    if len(trimmed) <= 110:
        return trimmed
    return f"{trimmed[:107]}..."


def _get_veterinary_notification_recipients(thread):
    if thread.assigned_veterinary_user_id:
        return [thread.assigned_veterinary_user]
    return list(get_veterinary_users())


def create_notification(
    *,
    recipient,
    actor,
    notification_type,
    title,
    body,
    thread=None,
):
    Notification.objects.create(
        recipient=recipient,
        actor=actor,
        notification_type=notification_type,
        title=title,
        body=_build_notification_body(body),
        action_url=build_thread_action_url(recipient, thread) if thread else "",
        thread=thread,
        cow=thread.cow if thread else None,
        insemination_request=thread.insemination_request if thread else None,
    )


@transaction.atomic
def send_thread_message(*, thread, sender, body, image=None):
    sender_role = get_role_slug_for_user(sender)
    message = ConversationMessage.objects.create(
        thread=thread,
        sender=sender,
        sender_role_snapshot=sender_role,
        body=body.strip(),
    )
    if image:
        MessageImageAttachment.objects.create(message=message, image=image)

    thread.last_message_at = message.created_at
    if sender_role == ROLE_VETERINARY:
        if thread.assigned_veterinary_user_id is None:
            thread.assigned_veterinary_user = sender
        thread.status = ConversationThread.STATUS_WAITING_FOR_FARMER
        thread.save()
        create_notification(
            recipient=thread.farmer,
            actor=sender,
            notification_type=Notification.TYPE_PROVIDER_REPLIED,
            title="New reply from the veterinary team",
            body=body,
            thread=thread,
        )
    else:
        thread.status = ConversationThread.STATUS_WAITING_FOR_VET
        thread.save()
        for recipient in _get_veterinary_notification_recipients(thread):
            create_notification(
                recipient=recipient,
                actor=sender,
                notification_type=Notification.TYPE_NEW_FARMER_MESSAGE,
                title=f"New farmer message from {thread.farmer.get_full_name().strip() or thread.farmer.username}",
                body=body,
                thread=thread,
            )
    return message


@transaction.atomic
def create_or_append_provider_thread(*, farmer, provider, body, image=None, cow=None):
    thread = (
        ConversationThread.objects.filter(
            farmer=farmer,
            provider_key=provider["key"],
        )
        .exclude(status=ConversationThread.STATUS_CLOSED)
        .order_by("-last_message_at", "-updated_at")
        .first()
    )
    if thread is None:
        thread = ConversationThread.objects.create(
            farmer=farmer,
            provider_key=provider["key"],
            provider_name_snapshot=provider["name"],
            provider_title_snapshot=provider.get("provider_title", ""),
            provider_service_type=provider.get("service_type", ""),
            subject=_build_thread_subject(provider, cow=cow),
            cow=cow,
            last_message_at=timezone.now(),
        )
    send_thread_message(thread=thread, sender=farmer, body=body, image=image)
    return thread
