"""Explainable milk-drop rules and synchronization for saved cow alerts."""

from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone

from .models import MilkProductionAlert, MilkRecord


BASELINE_RECORD_COUNT = 7
WARNING_DROP_PERCENT = Decimal("15")
CRITICAL_DROP_PERCENT = Decimal("25")
def evaluate_milk_drop(record, previous_yields):
    """Return one deterministic status using the seven previous recorded days."""
    previous_yields = [Decimal(value) for value in previous_yields]
    if len(previous_yields) < BASELINE_RECORD_COUNT:
        return {"level": "insufficient_history", "baseline_yield_liters": None}

    baseline = sum(previous_yields[-BASELINE_RECORD_COUNT:], Decimal("0")) / Decimal(
        BASELINE_RECORD_COUNT
    )
    if baseline == 0:
        return {"level": "unavailable", "baseline_yield_liters": Decimal("0")}

    current_yield = Decimal(record.daily_yield_liters)
    drop_percent = (baseline - current_yield) / baseline * Decimal("100")
    if drop_percent > CRITICAL_DROP_PERCENT:
        level = MilkProductionAlert.SEVERITY_CRITICAL
    elif drop_percent > WARNING_DROP_PERCENT:
        level = MilkProductionAlert.SEVERITY_WARNING
    else:
        level = "normal"

    return {
        "level": level,
        "baseline_yield_liters": baseline,
        "current_yield_liters": current_yield,
        "drop_percent": drop_percent,
    }


def _next_step(severity):
    if severity == MilkProductionAlert.SEVERITY_CRITICAL:
        return (
            "Check that the amount was entered correctly and observe the cow today. "
            "Contact a veterinary or extension worker if she seems unwell or the drop continues."
        )
    return (
        "Check that the amount was entered correctly, then watch the next milking "
        "to see whether production returns to usual."
    )


def _sync_alert(record, result):
    alert = MilkProductionAlert.objects.filter(
        cow_id=record.cow_id,
        record_date=record.record_date,
    ).first()
    severity = result["level"]
    if severity not in {
        MilkProductionAlert.SEVERITY_WARNING,
        MilkProductionAlert.SEVERITY_CRITICAL,
    }:
        if alert and alert.status != MilkProductionAlert.STATUS_RESOLVED:
            alert.status = MilkProductionAlert.STATUS_RESOLVED
            alert.resolved_at = timezone.now()
            alert.save(update_fields=["status", "resolved_at", "updated_at"])
        return

    old_severity = alert.severity if alert else None
    if alert is None:
        alert = MilkProductionAlert(cow_id=record.cow_id, record_date=record.record_date)
    if old_severity != severity or alert.status == MilkProductionAlert.STATUS_RESOLVED:
        alert.status = MilkProductionAlert.STATUS_ACTIVE
        alert.acknowledged_at = None
        alert.resolved_at = None
    alert.severity = severity
    alert.baseline_yield_liters = result["baseline_yield_liters"].quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    alert.current_yield_liters = result["current_yield_liters"].quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    alert.drop_percent = result["drop_percent"].quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    alert.next_step_text = _next_step(severity)
    alert.save()


@transaction.atomic
def recalculate_milk_alerts(cow, from_date):
    """Re-evaluate this cow from a changed date, including later baselines.

    A corrected historical entry can alter the next seven recorded results, so
    all later records are replayed in date order. Missing dates remain absent.
    """
    all_records = list(
        MilkRecord.objects.filter(cow=cow)
        .order_by("record_date")
        .only("id", "cow_id", "record_date", "daily_yield_liters")
    )
    previous_yields = []
    for record in all_records:
        if record.record_date >= from_date:
            _sync_alert(record, evaluate_milk_drop(record, previous_yields))
        previous_yields.append(Decimal(record.daily_yield_liters))


def acknowledge_milk_alert(alert):
    if alert.status != MilkProductionAlert.STATUS_ACTIVE:
        return alert
    alert.status = MilkProductionAlert.STATUS_ACKNOWLEDGED
    alert.acknowledged_at = timezone.now()
    alert.save(update_fields=["status", "acknowledged_at", "updated_at"])
    return alert
