from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from farmers_dashboard.models import Cow


class Command(BaseCommand):
    help = "Create or refresh sample cows for one existing farmer demo account."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            required=True,
            help="Username of the farmer account reserved for demonstrations.",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        try:
            farmer = User.objects.select_related("profile__role").get(
                username=options["username"]
            )
        except User.DoesNotExist as exc:
            raise CommandError("That farmer account does not exist.") from exc

        if not hasattr(farmer, "profile") or farmer.profile.dashboard_slug != "farmer":
            raise CommandError("Choose an account with the farmer role.")

        today = timezone.localdate()
        samples = [
            {
                "cow_number": "DEMO-ALERT-001",
                "name": "Amani",
                "breed": Cow.BREED_FRIESIAN,
                "reproductive_status": "",
                "expected_calving_date": None,
                "needs_attention": True,
                "attention_reason": "Eating less than usual.",
                "tracking_stage": Cow.STAGE_PREGNANT,
                "is_pregnant": True,
            },
            {
                "cow_number": "DEMO-ALERT-002",
                "name": "Neema",
                "breed": Cow.BREED_AYRSHIRE,
                "reproductive_status": Cow.REPRODUCTIVE_STATUS_NEAR_CALVING,
                "expected_calving_date": today + timedelta(days=7),
                "needs_attention": False,
                "attention_reason": "",
                "is_pregnant": True,
                "tracking_stage": Cow.STAGE_NEARING_CALVING,
            },
            {
                "cow_number": "DEMO-ALERT-003",
                "name": "Zuri",
                "breed": Cow.BREED_JERSEY,
                "reproductive_status": Cow.REPRODUCTIVE_STATUS_NEAR_CALVING,
                "expected_calving_date": today,
                "needs_attention": False,
                "attention_reason": "",
                "is_pregnant": True,
                "tracking_stage": Cow.STAGE_ACTIVE_LABOR,
            },
            {
                "cow_number": "DEMO-ALERT-004",
                "name": "Malaika",
                "breed": Cow.BREED_SAHIWAL,
                "reproductive_status": Cow.REPRODUCTIVE_STATUS_NOT_INSEMINATED,
                "expected_calving_date": None,
                "needs_attention": False,
                "attention_reason": "",
                "is_pregnant": False,
                "tracking_stage": Cow.STAGE_REGISTERED,
            },
        ]

        for sample in samples:
            sample_data = sample.copy()
            cow_number = sample_data.pop("cow_number")
            Cow.objects.update_or_create(
                owner=farmer,
                cow_number=cow_number,
                defaults=sample_data,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Prepared {len(samples)} demo cows for {farmer.username}. "
                "Only cows with DEMO-ALERT tags were changed."
            )
        )
