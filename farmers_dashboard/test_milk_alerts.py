from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from users.models import Profile, Role

from .milk_alerts import evaluate_milk_drop, recalculate_milk_alerts
from .models import Cow, MilkProductionAlert, MilkRecord


class MilkDropRuleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="milk-alert-farmer",
            password="StrongPass123!",
        )
        self.cow = Cow.objects.create(
            owner=self.user,
            cow_number="MILK-001",
            name="Amani",
            breed=Cow.BREED_FRIESIAN,
        )
        self.current_date = date(2026, 11, 13)

    def _current_record(self, yield_liters):
        return MilkRecord(
            cow=self.cow,
            record_date=self.current_date,
            daily_yield_liters=Decimal(yield_liters),
        )

    def test_severity_boundaries_are_explicit(self):
        baseline = [Decimal("10.00")] * 7

        self.assertEqual(evaluate_milk_drop(self._current_record("8.50"), baseline)["level"], "normal")
        self.assertEqual(evaluate_milk_drop(self._current_record("8.49"), baseline)["level"], "warning")
        self.assertEqual(evaluate_milk_drop(self._current_record("7.50"), baseline)["level"], "warning")
        self.assertEqual(evaluate_milk_drop(self._current_record("7.49"), baseline)["level"], "critical")

    def test_insufficient_and_zero_baselines_are_not_alerts(self):
        insufficient = evaluate_milk_drop(
            self._current_record("8.00"), [Decimal("10.00")] * 6
        )
        zero_baseline = evaluate_milk_drop(
            self._current_record("0.00"), [Decimal("0.00")] * 7
        )

        self.assertEqual(insufficient["level"], "insufficient_history")
        self.assertEqual(zero_baseline["level"], "unavailable")

    def test_saved_drop_alert_is_replayed_after_record_correction(self):
        for days_before in range(7, 0, -1):
            MilkRecord.objects.create(
                cow=self.cow,
                record_date=self.current_date - timedelta(days=days_before),
                daily_yield_liters="10.00",
            )
        current = MilkRecord.objects.create(
            cow=self.cow,
            record_date=self.current_date,
            daily_yield_liters="8.00",
        )

        recalculate_milk_alerts(self.cow, current.record_date)
        alert = MilkProductionAlert.objects.get(cow=self.cow, record_date=current.record_date)

        self.assertEqual(alert.severity, MilkProductionAlert.SEVERITY_WARNING)
        self.assertEqual(alert.drop_percent, Decimal("20.00"))
        self.assertEqual(alert.baseline_yield_liters, Decimal("10.00"))

        MilkRecord.objects.filter(pk=current.pk).update(daily_yield_liters="9.00")
        recalculate_milk_alerts(self.cow, current.record_date)
        alert.refresh_from_db()

        self.assertEqual(alert.status, MilkProductionAlert.STATUS_RESOLVED)

    def test_active_milk_alert_is_visible_on_farmer_dashboard(self):
        role, _ = Role.objects.get_or_create(
            slug="farmer",
            defaults={
                "name": "Farmer",
                "dashboard_namespace": "farmers_dashboard",
                "default_path": "/farmers/",
            },
        )
        Profile.objects.create(user=self.user, role=role)
        for days_before in range(7, 0, -1):
            MilkRecord.objects.create(
                cow=self.cow,
                record_date=self.current_date - timedelta(days=days_before),
                daily_yield_liters="10.00",
            )
        current = MilkRecord.objects.create(
            cow=self.cow,
            record_date=self.current_date,
            daily_yield_liters="8.00",
        )
        recalculate_milk_alerts(self.cow, current.record_date)
        self.client.force_login(self.user)

        response = self.client.get(reverse("farmers_dashboard:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Milk changes to check")
        self.assertContains(response, "Amani")
        self.assertContains(response, "down 20%")
        self.assertEqual(response.context["milk_drop_alerts"].count(), 1)

    def test_farmer_can_acknowledge_their_own_milk_alert(self):
        role, _ = Role.objects.get_or_create(
            slug="farmer",
            defaults={
                "name": "Farmer",
                "dashboard_namespace": "farmers_dashboard",
                "default_path": "/farmers/",
            },
        )
        Profile.objects.create(user=self.user, role=role)
        for days_before in range(7, 0, -1):
            MilkRecord.objects.create(
                cow=self.cow,
                record_date=self.current_date - timedelta(days=days_before),
                daily_yield_liters="10.00",
            )
        current = MilkRecord.objects.create(
            cow=self.cow,
            record_date=self.current_date,
            daily_yield_liters="8.00",
        )
        recalculate_milk_alerts(self.cow, current.record_date)
        alert = MilkProductionAlert.objects.get(cow=self.cow)
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("farmers_dashboard:milk_alert_acknowledge", args=[alert.pk])
        )

        alert.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(alert.status, MilkProductionAlert.STATUS_ACKNOWLEDGED)

    def test_farmer_cannot_acknowledge_another_farmers_alert(self):
        role, _ = Role.objects.get_or_create(
            slug="farmer",
            defaults={
                "name": "Farmer",
                "dashboard_namespace": "farmers_dashboard",
                "default_path": "/farmers/",
            },
        )
        Profile.objects.create(user=self.user, role=role)
        other_user = User.objects.create_user(username="other-milk-farmer")
        Profile.objects.create(user=other_user, role=role)
        other_cow = Cow.objects.create(
            owner=other_user,
            cow_number="MILK-OTHER",
            name="Neema",
            breed=Cow.BREED_FRIESIAN,
        )
        alert = MilkProductionAlert.objects.create(
            cow=other_cow,
            record_date=self.current_date,
            severity=MilkProductionAlert.SEVERITY_WARNING,
            baseline_yield_liters="10.00",
            current_yield_liters="8.00",
            drop_percent="20.00",
            next_step_text="Check this cow.",
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("farmers_dashboard:milk_alert_acknowledge", args=[alert.pk])
        )

        self.assertEqual(response.status_code, 404)
