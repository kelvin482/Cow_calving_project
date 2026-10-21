from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from .milk_features import calculate_milk_features
from .models import Cow, MilkRecord, ReproductiveEvent


class MilkFeatureCalculationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="feature-farmer",
            email="feature-farmer@example.test",
            password="StrongPass123!",
        )
        self.cow = Cow.objects.create(
            owner=self.user,
            cow_number="FEATURE-001",
            name="Feature cow",
            breed=Cow.BREED_FRIESIAN,
        )
        self.record_date = date(2026, 6, 1)

    def _record(self, days_before, yield_liters, cow=None):
        return MilkRecord.objects.create(
            cow=cow or self.cow,
            record_date=self.record_date - timedelta(days=days_before),
            daily_yield_liters=yield_liters,
        )

    def _current_record(self, yield_liters="16.00"):
        return MilkRecord(
            cow=self.cow,
            record_date=self.record_date,
            daily_yield_liters=yield_liters,
        )

    def test_calculates_features_from_previous_measured_days_only(self):
        for days_before in range(1, 6):
            self._record(days_before, Decimal("8.00") + days_before * 2)
        for days_before in range(8, 23):
            self._record(days_before, "10.00")
        self._record(31, "99.00")

        features = calculate_milk_features(self._current_record())

        self.assertEqual(features["current_yield_liters"], Decimal("16.00"))
        self.assertEqual(
            features["change_from_previous_7_day_average_percent"],
            Decimal("14.28571428571428571428571429"),
        )
        self.assertEqual(
            features["deviation_from_previous_30_day_average_liters"],
            Decimal("5.00"),
        )
        self.assertAlmostEqual(
            float(features["previous_7_day_standard_deviation_liters"]),
            2.8284271247461903,
        )
        self.assertEqual(features["previous_7_day_observation_count"], 5)
        self.assertEqual(features["previous_30_day_observation_count"], 20)
        self.assertIsNone(
            features["unavailable_reasons"][
                "deviation_from_previous_30_day_average_liters"
            ]
        )

    def test_calendar_windows_include_day_seven_but_not_day_eight_or_day_31(self):
        for days_before in range(1, 5):
            self._record(days_before, "10.00")
        self._record(7, "10.00")
        for days_before in range(10, 24):
            self._record(days_before, "10.00")
        self._record(8, "99.00")
        self._record(31, "99.00")

        features = calculate_milk_features(self._current_record())

        self.assertEqual(features["previous_7_day_observation_count"], 5)
        self.assertEqual(features["previous_30_day_observation_count"], 20)
        self.assertEqual(
            features["deviation_from_previous_30_day_average_liters"],
            Decimal("1.55"),
        )

    def test_insufficient_history_leaves_baseline_features_unavailable(self):
        for days_before in range(1, 5):
            self._record(days_before, "10.00")
        for days_before in range(8, 23):
            self._record(days_before, "10.00")

        features = calculate_milk_features(self._current_record())

        self.assertIsNone(features["change_from_previous_7_day_average_percent"])
        self.assertIsNone(features["previous_7_day_standard_deviation_liters"])
        self.assertIsNone(features["deviation_from_previous_30_day_average_liters"])
        self.assertEqual(
            features["unavailable_reasons"]["change_from_previous_7_day_average_percent"],
            "insufficient_history",
        )
        self.assertEqual(
            features["unavailable_reasons"]["deviation_from_previous_30_day_average_liters"],
            "insufficient_history",
        )

    def test_zero_seven_day_baseline_has_no_percentage_change(self):
        for days_before in range(1, 21):
            self._record(days_before, "0.00")

        features = calculate_milk_features(self._current_record("2.00"))

        self.assertIsNone(features["change_from_previous_7_day_average_percent"])
        self.assertEqual(
            features["unavailable_reasons"]["change_from_previous_7_day_average_percent"],
            "zero_baseline",
        )
        self.assertEqual(
            features["deviation_from_previous_30_day_average_liters"],
            Decimal("2.00"),
        )

    def test_days_in_milk_uses_latest_calving_event_on_or_before_record_date(self):
        ReproductiveEvent.objects.create(
            cow=self.cow,
            recorded_by=self.user,
            event_type=ReproductiveEvent.EVENT_CALVED,
            event_date=self.record_date - timedelta(days=40),
        )
        ReproductiveEvent.objects.create(
            cow=self.cow,
            recorded_by=self.user,
            event_type=ReproductiveEvent.EVENT_CALVED,
            event_date=self.record_date - timedelta(days=9),
        )
        ReproductiveEvent.objects.create(
            cow=self.cow,
            recorded_by=self.user,
            event_type=ReproductiveEvent.EVENT_CALVED,
            event_date=self.record_date + timedelta(days=1),
        )

        features = calculate_milk_features(self._current_record())

        self.assertEqual(features["days_in_milk"], 10)
        self.assertIsNone(features["unavailable_reasons"]["days_in_milk"])

    def test_missing_calving_event_leaves_days_in_milk_unavailable(self):
        features = calculate_milk_features(self._current_record())

        self.assertIsNone(features["days_in_milk"])
        self.assertEqual(
            features["unavailable_reasons"]["days_in_milk"],
            "no_prior_calving_event",
        )

    def test_history_from_another_cow_is_not_included(self):
        other_cow = Cow.objects.create(
            owner=self.user,
            cow_number="FEATURE-002",
            name="Other feature cow",
            breed=Cow.BREED_FRIESIAN,
        )
        for days_before in range(1, 31):
            self._record(days_before, "10.00", cow=other_cow)

        features = calculate_milk_features(self._current_record())

        self.assertEqual(features["previous_7_day_observation_count"], 0)
        self.assertEqual(features["previous_30_day_observation_count"], 0)
        self.assertIsNone(features["change_from_previous_7_day_average_percent"])
        self.assertIsNone(features["deviation_from_previous_30_day_average_liters"])

    def test_unsaved_cow_or_missing_measurement_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_milk_features(
                MilkRecord(
                    record_date=self.record_date,
                    daily_yield_liters="1.00",
                )
            )
        with self.assertRaises(ValueError):
            calculate_milk_features(MilkRecord(cow=self.cow, record_date=self.record_date))
