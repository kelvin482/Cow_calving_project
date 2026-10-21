"""Deterministic historical features for one cow's daily milk record."""

from datetime import timedelta
from decimal import Decimal

from .models import MilkRecord, ReproductiveEvent


SEVEN_DAY_WINDOW = 7
THIRTY_DAY_WINDOW = 30
MIN_SEVEN_DAY_OBSERVATIONS = 5
MIN_THIRTY_DAY_OBSERVATIONS = 20


def _average(values):
    return sum(values, Decimal("0")) / Decimal(len(values))


def _population_standard_deviation(values):
    average = _average(values)
    variance = sum(
        ((value - average) ** 2 for value in values),
        Decimal("0"),
    ) / Decimal(len(values))
    return variance.sqrt()


def calculate_milk_features(record):
    """Calculate historical features without filling gaps or using future data.

    Windows cover the preceding calendar days and exclude the current record.
    Missing dates contribute no value; observation counts make insufficient
    baselines explicit to callers.
    """
    if not isinstance(record, MilkRecord):
        raise TypeError("record must be a MilkRecord instance")
    if record.cow_id is None or record.record_date is None:
        raise ValueError("record must have a cow and record date")
    if record.daily_yield_liters is None:
        raise ValueError("record must have a measured daily yield")

    current_yield = Decimal(record.daily_yield_liters)
    if current_yield < 0:
        raise ValueError("daily yield cannot be negative")

    previous_records = MilkRecord.objects.filter(
        cow_id=record.cow_id,
        record_date__lt=record.record_date,
        record_date__gte=record.record_date - timedelta(days=THIRTY_DAY_WINDOW),
    ).order_by("record_date")
    previous_values = list(
        previous_records.values_list("record_date", "daily_yield_liters")
    )

    seven_day_start = record.record_date - timedelta(days=SEVEN_DAY_WINDOW)
    seven_day_values = [
        value for record_date, value in previous_values if record_date >= seven_day_start
    ]
    thirty_day_values = [value for _, value in previous_values]

    seven_day_count = len(seven_day_values)
    thirty_day_count = len(thirty_day_values)
    unavailable_reasons = {}

    if seven_day_count < MIN_SEVEN_DAY_OBSERVATIONS:
        seven_day_change = None
        seven_day_stddev = None
        unavailable_reasons["change_from_previous_7_day_average_percent"] = (
            "insufficient_history"
        )
        unavailable_reasons["previous_7_day_standard_deviation_liters"] = (
            "insufficient_history"
        )
    else:
        seven_day_average = _average(seven_day_values)
        if seven_day_average == 0:
            seven_day_change = None
            unavailable_reasons["change_from_previous_7_day_average_percent"] = (
                "zero_baseline"
            )
        else:
            seven_day_change = (
                (current_yield - seven_day_average)
                / seven_day_average
                * Decimal("100")
            )
            unavailable_reasons["change_from_previous_7_day_average_percent"] = None
        seven_day_stddev = _population_standard_deviation(seven_day_values)
        unavailable_reasons["previous_7_day_standard_deviation_liters"] = None

    if thirty_day_count < MIN_THIRTY_DAY_OBSERVATIONS:
        thirty_day_deviation = None
        unavailable_reasons["deviation_from_previous_30_day_average_liters"] = (
            "insufficient_history"
        )
    else:
        thirty_day_deviation = current_yield - _average(thirty_day_values)
        unavailable_reasons["deviation_from_previous_30_day_average_liters"] = None

    calving_event = (
        ReproductiveEvent.objects.filter(
            cow_id=record.cow_id,
            event_type=ReproductiveEvent.EVENT_CALVED,
            event_date__lte=record.record_date,
        )
        .order_by("-event_date", "-created_at")
        .first()
    )
    if calving_event:
        days_in_milk = (record.record_date - calving_event.event_date).days + 1
        unavailable_reasons["days_in_milk"] = None
    else:
        days_in_milk = None
        unavailable_reasons["days_in_milk"] = "no_prior_calving_event"

    return {
        "current_yield_liters": current_yield,
        "change_from_previous_7_day_average_percent": seven_day_change,
        "deviation_from_previous_30_day_average_liters": thirty_day_deviation,
        "previous_7_day_standard_deviation_liters": seven_day_stddev,
        "days_in_milk": days_in_milk,
        "previous_7_day_observation_count": seven_day_count,
        "previous_30_day_observation_count": thirty_day_count,
        "unavailable_reasons": unavailable_reasons,
    }
