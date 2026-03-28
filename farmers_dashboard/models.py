from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property


class InseminationRequest(models.Model):
    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    cow = models.ForeignKey(
        "Cow",
        on_delete=models.CASCADE,
        related_name="insemination_requests",
    )
    farmer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="insemination_requests",
    )
    service_type = models.CharField(
        max_length=32,
        choices=[
            ("artificial_insemination", "Artificial insemination"),
            ("natural_service", "Natural service"),
        ],
        blank=True,
        default="",
    )
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    request_note = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.cow.name} insemination request ({self.get_status_display()})"

    @property
    def is_open(self):
        return self.status in {self.STATUS_PENDING, self.STATUS_ACCEPTED}

    @property
    def status_tone(self):
        if self.status == self.STATUS_ACCEPTED:
            return "sky"
        if self.status == self.STATUS_COMPLETED:
            return "emerald"
        if self.status == self.STATUS_CANCELLED:
            return "slate"
        return "amber"

    @property
    def next_step_text(self):
        if self.status == self.STATUS_ACCEPTED:
            return "A provider has picked up the request. Keep the cow ready for service."
        if self.status == self.STATUS_COMPLETED:
            return "Service is complete. Record the insemination date to continue the tracker."
        if self.status == self.STATUS_CANCELLED:
            return "This request is closed. Create a fresh request if support is still needed."
        return "Your request is waiting for follow-up. Keep heat signs and timing visible."


class ReproductiveEvent(models.Model):
    EVENT_HEAT_OBSERVED = "heat_observed"
    EVENT_INSEMINATION_RECORDED = "insemination_recorded"
    EVENT_PREGNANCY_CONFIRMED = "pregnancy_confirmed"
    EVENT_PREGNANCY_NOT_KEPT = "pregnancy_not_kept"
    EVENT_CALVED = "calved"

    EVENT_TYPE_CHOICES = [
        (EVENT_HEAT_OBSERVED, "Heat observed"),
        (EVENT_INSEMINATION_RECORDED, "Insemination recorded"),
        (EVENT_PREGNANCY_CONFIRMED, "Pregnancy confirmed"),
        (EVENT_PREGNANCY_NOT_KEPT, "Pregnancy not kept"),
        (EVENT_CALVED, "Calved"),
    ]

    cow = models.ForeignKey(
        "Cow",
        on_delete=models.CASCADE,
        related_name="reproductive_events",
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reproductive_events",
    )
    event_type = models.CharField(max_length=32, choices=EVENT_TYPE_CHOICES)
    event_date = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-event_date", "-created_at"]

    def __str__(self):
        return f"{self.cow.name} {self.get_event_type_display()} ({self.event_date:%d %b %Y})"

    @property
    def tone(self):
        if self.event_type == self.EVENT_HEAT_OBSERVED:
            return "orange"
        if self.event_type == self.EVENT_INSEMINATION_RECORDED:
            return "sky"
        if self.event_type == self.EVENT_PREGNANCY_CONFIRMED:
            return "emerald"
        if self.event_type == self.EVENT_PREGNANCY_NOT_KEPT:
            return "rose"
        return "amber"


class ServiceProviderMessage(models.Model):
    STATUS_SENT = "sent"
    STATUS_READ = "read"

    STATUS_CHOICES = [
        (STATUS_SENT, "Sent"),
        (STATUS_READ, "Read"),
    ]

    SERVICE_TYPE_VETERINARY = "veterinary"
    SERVICE_TYPE_ARTIFICIAL_INSEMINATION = "artificial_insemination"

    SERVICE_TYPE_CHOICES = [
        (SERVICE_TYPE_VETERINARY, "Veterinary"),
        (SERVICE_TYPE_ARTIFICIAL_INSEMINATION, "Artificial insemination"),
    ]

    farmer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="service_provider_messages",
    )
    provider_key = models.CharField(max_length=64)
    provider_name = models.CharField(max_length=120)
    provider_title = models.CharField(max_length=120)
    provider_service_type = models.CharField(
        max_length=32,
        choices=SERVICE_TYPE_CHOICES,
    )
    provider_county = models.CharField(max_length=64)
    provider_phone = models.CharField(max_length=32, blank=True)
    provider_email = models.EmailField(blank=True)
    message = models.TextField()
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_SENT,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.provider_name} message from {self.farmer}"


class Cow(models.Model):
    BREED_FRIESIAN = "friesian"
    BREED_AYRSHIRE = "ayrshire"
    BREED_JERSEY = "jersey"
    BREED_GUERNSEY = "guernsey"
    BREED_SAHIWAL = "sahiwal"
    BREED_CROSSBREED = "crossbreed"
    BREED_OTHER = "other"

    BREED_CHOICES = [
        (BREED_FRIESIAN, "Friesian"),
        (BREED_AYRSHIRE, "Ayrshire"),
        (BREED_JERSEY, "Jersey"),
        (BREED_GUERNSEY, "Guernsey"),
        (BREED_SAHIWAL, "Sahiwal"),
        (BREED_CROSSBREED, "Crossbreed"),
        (BREED_OTHER, "Other"),
    ]

    REPRODUCTIVE_STATUS_NOT_INSEMINATED = "not_inseminated"
    REPRODUCTIVE_STATUS_INSEMINATED = "inseminated"
    REPRODUCTIVE_STATUS_PREGNANCY_CONFIRMED = "pregnancy_confirmed"
    REPRODUCTIVE_STATUS_NEAR_CALVING = "near_calving"

    REPRODUCTIVE_STATUS_CHOICES = [
        (REPRODUCTIVE_STATUS_NOT_INSEMINATED, "Not inseminated yet"),
        (REPRODUCTIVE_STATUS_INSEMINATED, "Already inseminated"),
        (REPRODUCTIVE_STATUS_PREGNANCY_CONFIRMED, "Pregnancy confirmed"),
        (REPRODUCTIVE_STATUS_NEAR_CALVING, "Near calving"),
    ]

    INSEMINATION_TYPE_ARTIFICIAL = "artificial_insemination"
    INSEMINATION_TYPE_NATURAL = "natural_service"

    INSEMINATION_TYPE_CHOICES = [
        (INSEMINATION_TYPE_ARTIFICIAL, "Artificial insemination"),
        (INSEMINATION_TYPE_NATURAL, "Natural service"),
    ]

    STAGE_REGISTERED = "registered"
    STAGE_INSEMINATED = "inseminated"
    STAGE_PREGNANT = "pregnant"
    STAGE_NEARING_CALVING = "nearing_calving"
    STAGE_ACTIVE_LABOR = "active_labor"
    STAGE_POST_CALVING = "post_calving"

    TRACKING_STAGE_CHOICES = [
        (STAGE_REGISTERED, "Registered"),
        (STAGE_INSEMINATED, "Inseminated"),
        (STAGE_PREGNANT, "Pregnant"),
        (STAGE_NEARING_CALVING, "Nearing calving"),
        (STAGE_ACTIVE_LABOR, "Active labor"),
        (STAGE_POST_CALVING, "Post-calving"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cows",
    )
    cow_number = models.CharField(max_length=40)
    name = models.CharField(max_length=120)
    breed = models.CharField(max_length=40, choices=BREED_CHOICES)
    date_of_birth = models.DateField(blank=True, null=True)
    reproductive_status = models.CharField(
        max_length=32,
        choices=REPRODUCTIVE_STATUS_CHOICES,
        blank=True,
        default="",
    )
    last_heat_date = models.DateField(blank=True, null=True)
    insemination_type = models.CharField(
        max_length=32,
        choices=INSEMINATION_TYPE_CHOICES,
        blank=True,
        default="",
    )
    insemination_date = models.DateField(blank=True, null=True)
    pregnancy_confirmation_date = models.DateField(blank=True, null=True)
    expected_calving_date = models.DateField(blank=True, null=True)
    is_pregnant = models.BooleanField(default=False)
    is_lactating = models.BooleanField(default=False)
    needs_attention = models.BooleanField(default=False)
    tracking_stage = models.CharField(
        max_length=32,
        choices=TRACKING_STAGE_CHOICES,
        default=STAGE_REGISTERED,
    )
    photo = models.FileField(
        upload_to="cow_photos/",
        blank=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=["jpg", "jpeg", "png", "webp", "gif"]
            )
        ],
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "cow_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "cow_number"],
                name="unique_cow_number_per_owner",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.cow_number})"

    @cached_property
    def active_insemination_request(self):
        prefetched_requests = getattr(self, "_prefetched_objects_cache", {}).get(
            "insemination_requests"
        )
        request_list = prefetched_requests if prefetched_requests is not None else self.insemination_requests.all()
        for request in request_list:
            if request.is_open:
                return request
        return None

    def is_due_this_month(self):
        if not self.expected_calving_date:
            return False
        today = timezone.localdate()
        return (
            self.expected_calving_date.year == today.year
            and self.expected_calving_date.month == today.month
        )

    def is_nearing_calving(self):
        if not self.expected_calving_date:
            return False
        days_until_due = (self.expected_calving_date - timezone.localdate()).days
        return 0 <= days_until_due <= 30

    @cached_property
    def photo_url(self):
        return self.photo.url if self.photo else ""

    @property
    def reproductive_status_label(self):
        if self.reproductive_status:
            return dict(self.REPRODUCTIVE_STATUS_CHOICES).get(
                self.reproductive_status,
                "Reproductive status",
            )
        if self.is_nearing_calving():
            return "Near calving"
        if self.is_pregnant:
            return "Pregnancy confirmed"
        return "Registered"

    @property
    def status_tone(self):
        if self.needs_attention:
            return "rose"
        if self.is_nearing_calving():
            return "amber"
        if self.tracking_stage == self.STAGE_INSEMINATED:
            return "violet"
        if self.is_pregnant:
            return "sky"
        return "emerald"

    @property
    def status_label(self):
        if self.needs_attention:
            return "Needs attention"
        if self.tracking_stage == self.STAGE_ACTIVE_LABOR:
            return "Active labor"
        if self.tracking_stage == self.STAGE_POST_CALVING:
            return "Post-calving"
        if self.is_nearing_calving():
            return "Nearing calving"
        if self.tracking_stage == self.STAGE_INSEMINATED:
            return "Inseminated"
        if self.is_pregnant:
            return "Pregnant"
        return "Registered"

    @property
    def summary_text(self):
        if self.tracking_stage == self.STAGE_POST_CALVING:
            return "Calving recorded and recovery follow-up can continue"
        if self.tracking_stage == self.STAGE_ACTIVE_LABOR:
            return "Labour is active and needs close observation"
        if self.reproductive_status == self.REPRODUCTIVE_STATUS_NOT_INSEMINATED:
            if self.active_insemination_request:
                submitted_on = timezone.localtime(
                    self.active_insemination_request.submitted_at
                ).date()
                return f"Insemination request sent {submitted_on:%d %b %Y}"
            if self.last_heat_date:
                return f"Last heat observed {self.last_heat_date:%d %b %Y}"
            return "Ready for insemination planning"
        if self.insemination_date and self.tracking_stage == self.STAGE_INSEMINATED:
            return f"Inseminated on {self.insemination_date:%d %b %Y}"
        if self.pregnancy_confirmation_date:
            return (
                f"Pregnancy confirmed {self.pregnancy_confirmation_date:%d %b %Y}"
            )
        if self.expected_calving_date and self.is_nearing_calving():
            return f"Expected calving {self.expected_calving_date:%d %b %Y}"
        if self.expected_calving_date and self.is_pregnant:
            return f"Expected calving {self.expected_calving_date:%d %b %Y}"
        if self.is_lactating:
            return "Currently lactating"
        return "Cow profile ready for tracking"

    @property
    def alert_category(self):
        if self.needs_attention:
            return "Needs attention"
        if self.tracking_stage == self.STAGE_ACTIVE_LABOR:
            return "Active labor"
        if self.is_nearing_calving():
            return "Nearing calving"
        if self.tracking_stage == self.STAGE_INSEMINATED:
            return "Inseminated"
        if self.is_pregnant:
            return "Pregnant"
        return "Registered"

    @property
    def next_action_text(self):
        if self.active_insemination_request:
            return self.active_insemination_request.next_step_text
        if self.needs_attention:
            return "Review the cow and open support if the issue continues."
        if self.tracking_stage == self.STAGE_ACTIVE_LABOR:
            return "Track labour progress closely and prepare for escalation."
        if self.tracking_stage == self.STAGE_POST_CALVING:
            return "Monitor recovery, keep the calf safe, and record the next heat when ready."
        if self.tracking_stage == self.STAGE_INSEMINATED:
            return "Keep watch after service and plan the pregnancy check."
        if self.is_nearing_calving():
            return "Start calving watch and keep the pen ready."
        if self.is_pregnant:
            return "Keep pregnancy follow-up and calving dates visible."
        if self.reproductive_status == self.REPRODUCTIVE_STATUS_NOT_INSEMINATED:
            return "Keep heat dates visible and prepare the next insemination step."
        return "Complete registration details and start tracking when ready."
