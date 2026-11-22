import logging

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse

from .models import MilkProductionAlert


logger = logging.getLogger(__name__)


def email_farmer_about_alert(alert_id):
    """Email the cow owner after a new or changed milk alert commits."""
    try:
        alert = MilkProductionAlert.objects.select_related("cow__owner").get(
            pk=alert_id
        )
    except MilkProductionAlert.DoesNotExist:
        logger.warning("Milk alert %s disappeared before its email was sent.", alert_id)
        return

    farmer = alert.cow.owner
    if not farmer.email:
        logger.info("Skipping milk alert email for farmer %s without an email.", farmer.pk)
        return

    alert_path = reverse("farmers_dashboard:alerts")
    alert_url = f"{settings.SITE_URL}{alert_path}"
    farmer_name = farmer.get_full_name().strip() or farmer.username
    subject = f"{alert.get_severity_display()} milk alert for {alert.cow.name}"
    body = (
        f"Hello {farmer_name},\n\n"
        f"CowCalving noticed a {alert.get_severity_display().lower()} milk drop for "
        f"{alert.cow.name} on {alert.record_date:%d %B %Y}. The recorded yield was "
        f"{alert.current_yield_liters} L, down {alert.drop_percent}% from the "
        f"seven-record average of {alert.baseline_yield_liters} L.\n\n"
        f"Suggested next step: {alert.next_step_text}\n\n"
        "This is a prompt to check the records and observe the cow; it is not a diagnosis.\n\n"
        f"Review your alerts: {alert_url}\n"
    )

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[farmer.email],
            fail_silently=False,
        )
    except Exception:
        # Alert persistence should not fail because an external mail provider is down.
        logger.exception("Could not email farmer %s about milk alert %s.", farmer.pk, alert.pk)
