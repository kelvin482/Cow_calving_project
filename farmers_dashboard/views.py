import math
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Case, Count, IntegerField, Prefetch, When
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from communications.forms import ConversationReplyForm
from communications.models import ConversationThread
from communications.services import (
    create_or_append_provider_thread,
    get_notifications_for_user,
    get_thread_for_user,
    get_threads_for_user,
    get_unread_notification_count,
    get_unread_thread_count,
    get_veterinary_users,
    mark_notification_read,
    mark_thread_messages_read,
    send_thread_message,
)
from users.permissions import role_required
from users.services import get_profile

from .forms import (
    AttentionReasonForm,
    CowRegistrationForm,
    FarmLocationForm,
    MilkAlertCheckForm,
    MilkRecordForm,
    ReproductiveEventForm,
    ServiceProviderMessageForm,
)
from .models import (
    Cow,
    InseminationRequest,
    MilkRecord,
    MilkProductionAlert,
    ReproductiveEvent,
    ServiceProviderMessage,
)
from .milk_alerts import acknowledge_milk_alert, evaluate_milk_drop, recalculate_milk_alerts


KENYA_COUNTY_OPTIONS = [
    ("baringo", "Baringo County"),
    ("bomet", "Bomet County"),
    ("bungoma", "Bungoma County"),
    ("busia", "Busia County"),
    ("elgeyo-marakwet", "Elgeyo-Marakwet County"),
    ("embu", "Embu County"),
    ("garissa", "Garissa County"),
    ("homa-bay", "Homa Bay County"),
    ("isiolo", "Isiolo County"),
    ("kajiado", "Kajiado County"),
    ("kakamega", "Kakamega County"),
    ("kericho", "Kericho County"),
    ("kiambu", "Kiambu County"),
    ("kilifi", "Kilifi County"),
    ("kirinyaga", "Kirinyaga County"),
    ("kisii", "Kisii County"),
    ("kisumu", "Kisumu County"),
    ("kitui", "Kitui County"),
    ("kwale", "Kwale County"),
    ("laikipia", "Laikipia County"),
    ("lamu", "Lamu County"),
    ("machakos", "Machakos County"),
    ("makueni", "Makueni County"),
    ("mandera", "Mandera County"),
    ("marsabit", "Marsabit County"),
    ("meru", "Meru County"),
    ("migori", "Migori County"),
    ("mombasa", "Mombasa County"),
    ("muranga", "Murang'a County"),
    ("nairobi", "Nairobi County"),
    ("nakuru", "Nakuru County"),
    ("nandi", "Nandi County"),
    ("narok", "Narok County"),
    ("nyamira", "Nyamira County"),
    ("nyandarua", "Nyandarua County"),
    ("nyeri", "Nyeri County"),
    ("samburu", "Samburu County"),
    ("siaya", "Siaya County"),
    ("taita-taveta", "Taita-Taveta County"),
    ("tana-river", "Tana River County"),
    ("tharaka-nithi", "Tharaka-Nithi County"),
    ("trans-nzoia", "Trans Nzoia County"),
    ("turkana", "Turkana County"),
    ("uasin-gishu", "Uasin Gishu County"),
    ("vihiga", "Vihiga County"),
    ("wajir", "Wajir County"),
    ("west-pokot", "West Pokot County"),
]

SERVICE_TYPE_VETERINARY = "veterinary"
SERVICE_TYPE_ARTIFICIAL_INSEMINATION = "artificial_insemination"

SERVICE_TYPE_OPTIONS = [
    (SERVICE_TYPE_VETERINARY, "Veterinary"),
    (SERVICE_TYPE_ARTIFICIAL_INSEMINATION, "Artificial insemination"),
]

KENYA_MAP_CENTER = {"lat": -0.023559, "lng": 37.906193}

# Keep the provider directory in code until the self-serve registration flow
# for professionals is added, so the farmer support page stays demo-ready.
SERVICE_PROVIDER_DIRECTORY = [
    {
        "name": "Dr. James Mwangi",
        "provider_title": "Large animal veterinarian",
        "county": "nairobi",
        "county_label": "Nairobi County",
        "service_type": SERVICE_TYPE_VETERINARY,
        "service_type_label": "Veterinary",
        "summary": "Experienced large animal veterinarian supporting dairy herd health, calving readiness, and urgent reproductive follow-up.",
        "phone": "+254712345678",
        "email": "jmwangi@vetkenya.co.ke",
        "coverage": "Nairobi and nearby peri-urban farms",
        "availability": "Same-day callback",
        "is_verified": True,
    },
    {
        "name": "Dr. Grace Wanjiku",
        "provider_title": "Fertility and herd veterinarian",
        "county": "kiambu",
        "county_label": "Kiambu County",
        "service_type": SERVICE_TYPE_VETERINARY,
        "service_type_label": "Veterinary",
        "summary": "Focuses on fertility checks, pregnancy confirmation, post-calving review, and milk herd health visits.",
        "phone": "+254723456789",
        "email": "gwanjiku@vetkenya.co.ke",
        "coverage": "Kiambu, Limuru, and Githunguri",
        "availability": "Available this afternoon",
        "is_verified": True,
    },
    {
        "name": "Dr. Peter Kiptoo",
        "provider_title": "Dairy field veterinarian",
        "county": "uasin-gishu",
        "county_label": "Uasin Gishu County",
        "service_type": SERVICE_TYPE_VETERINARY,
        "service_type_label": "Veterinary",
        "summary": "Supports large dairy farms with heat follow-up, calving supervision, calf recovery, and herd vaccination planning.",
        "phone": "+254734567890",
        "email": "pkiptoo@riftvet.co.ke",
        "coverage": "Eldoret and surrounding dairy belt",
        "availability": "Morning rounds only",
        "is_verified": True,
    },
    {
        "name": "Dr. Mercy Atieno",
        "provider_title": "Reproductive health veterinarian",
        "county": "kisumu",
        "county_label": "Kisumu County",
        "service_type": SERVICE_TYPE_VETERINARY,
        "service_type_label": "Veterinary",
        "summary": "Handles reproductive health reviews, difficult calving follow-up, and newborn calf stabilization for smallholder farms.",
        "phone": "+254745678901",
        "email": "matieno@lakevet.co.ke",
        "coverage": "Kisumu and Nyando corridor",
        "availability": "Responds within 2 hours",
        "is_verified": True,
    },
    {
        "name": "Dr. John Kamau",
        "provider_title": "Preventive care veterinarian",
        "county": "nakuru",
        "county_label": "Nakuru County",
        "service_type": SERVICE_TYPE_VETERINARY,
        "service_type_label": "Veterinary",
        "summary": "Offers herd fertility planning, retained placenta follow-up, and preventive dairy farm check-ins.",
        "phone": "+254756789012",
        "email": "jkamau@highlandvet.co.ke",
        "coverage": "Nakuru town, Molo, and Subukia",
        "availability": "On-call for urgent calving cases",
        "is_verified": True,
    },
    {
        "name": "Dr. Lucy Muthoni",
        "provider_title": "Mountain dairy veterinarian",
        "county": "nyeri",
        "county_label": "Nyeri County",
        "service_type": SERVICE_TYPE_VETERINARY,
        "service_type_label": "Veterinary",
        "summary": "Supports mountain dairy farms with breeding decisions, post-service review, and postpartum recovery checks.",
        "phone": "+254767890123",
        "email": "lmuthoni@centralvet.co.ke",
        "coverage": "Nyeri, Othaya, and Kieni",
        "availability": "Book for next-day visits",
        "is_verified": True,
    },
    {
        "name": "Dr. Brian Mutua",
        "provider_title": "Mixed dairy veterinarian",
        "county": "machakos",
        "county_label": "Machakos County",
        "service_type": SERVICE_TYPE_VETERINARY,
        "service_type_label": "Veterinary",
        "summary": "Works with mixed dairy operations on reproductive case reviews, calf health, and emergency labour escalation.",
        "phone": "+254778901234",
        "email": "bmutua@easternvet.co.ke",
        "coverage": "Machakos, Kangundo, and Athi River",
        "availability": "Next available slot tomorrow",
        "is_verified": True,
    },
    {
        "name": "Dr. Faith Akinyi",
        "provider_title": "Dairy reproduction veterinarian",
        "county": "kakamega",
        "county_label": "Kakamega County",
        "service_type": SERVICE_TYPE_VETERINARY,
        "service_type_label": "Veterinary",
        "summary": "Specialises in dairy cow reproductive management, clean calving setup, and first-day calf care.",
        "phone": "+254789012345",
        "email": "fakinyi@westernvet.co.ke",
        "coverage": "Kakamega and nearby western counties",
        "availability": "Weekend support available",
        "is_verified": True,
    },
    {
        "name": "Dr. Daniel Kibet",
        "provider_title": "Breeding and fertility veterinarian",
        "county": "kericho",
        "county_label": "Kericho County",
        "service_type": SERVICE_TYPE_VETERINARY,
        "service_type_label": "Veterinary",
        "summary": "Helps farmers plan insemination timing, confirm pregnancy windows, and reduce repeat breeding losses.",
        "phone": "+254790123456",
        "email": "dkibet@highlandanimalcare.co.ke",
        "coverage": "Kericho and Bureti farms",
        "availability": "Available this evening",
        "is_verified": True,
    },
    {
        "name": "Dr. Esther Kathure",
        "provider_title": "Calf survival and fertility veterinarian",
        "county": "meru",
        "county_label": "Meru County",
        "service_type": SERVICE_TYPE_VETERINARY,
        "service_type_label": "Veterinary",
        "summary": "Supports calf survival, difficult deliveries, dairy fertility follow-up, and routine farm visits for growing herds.",
        "phone": "+254701234567",
        "email": "ekathure@uppereastvet.co.ke",
        "coverage": "Meru central and nearby dairy areas",
        "availability": "Responds within 24 hours",
        "is_verified": True,
    },
    {
        "name": "Samuel Njoroge",
        "provider_title": "Artificial insemination technician",
        "county": "kiambu",
        "county_label": "Kiambu County",
        "service_type": SERVICE_TYPE_ARTIFICIAL_INSEMINATION,
        "service_type_label": "Artificial insemination",
        "summary": "Supports heat timing, semen handling, and on-farm artificial insemination for smallholder dairy herds.",
        "phone": "+254711223344",
        "email": "snjoroge@aibreeding.co.ke",
        "coverage": "Kiambu, Ruiru, and Juja farms",
        "availability": "Available this morning",
        "is_verified": True,
    },
    {
        "name": "Mary Chebet",
        "provider_title": "AI field officer",
        "county": "nakuru",
        "county_label": "Nakuru County",
        "service_type": SERVICE_TYPE_ARTIFICIAL_INSEMINATION,
        "service_type_label": "Artificial insemination",
        "summary": "Provides service timing support, artificial insemination visits, and repeat-breeding follow-up.",
        "phone": "+254722334455",
        "email": "mchebet@aibreeding.co.ke",
        "coverage": "Nakuru, Molo, and Njoro",
        "availability": "Next slot this afternoon",
        "is_verified": True,
    },
    {
        "name": "Kevin Oloo",
        "provider_title": "AI technician",
        "county": "kisumu",
        "county_label": "Kisumu County",
        "service_type": SERVICE_TYPE_ARTIFICIAL_INSEMINATION,
        "service_type_label": "Artificial insemination",
        "summary": "Helps farmers act within the breeding window and record artificial insemination dates correctly.",
        "phone": "+254733445566",
        "email": "koloo@aibreeding.co.ke",
        "coverage": "Kisumu, Nyando, and Muhoroni corridor",
        "availability": "Responds within 2 hours",
        "is_verified": True,
    },
    {
        "name": "Tabitha Mutheu",
        "provider_title": "Reproductive service technician",
        "county": "machakos",
        "county_label": "Machakos County",
        "service_type": SERVICE_TYPE_ARTIFICIAL_INSEMINATION,
        "service_type_label": "Artificial insemination",
        "summary": "Supports artificial insemination visits, service readiness checks, and breeding follow-up for dairy cows.",
        "phone": "+254744556677",
        "email": "tmutheu@aibreeding.co.ke",
        "coverage": "Machakos, Kangundo, and Athi River",
        "availability": "Book for same-day visit",
        "is_verified": True,
    },
]

for provider in SERVICE_PROVIDER_DIRECTORY:
    provider["key"] = f'{provider["service_type"]}-{slugify(provider["name"])}'

SERVICE_PROVIDER_DIRECTORY_BY_KEY = {
    provider["key"]: provider for provider in SERVICE_PROVIDER_DIRECTORY
}


TRACKING_STEPS = [
    (Cow.STAGE_REGISTERED, "Registered"),
    (Cow.STAGE_INSEMINATED, "Inseminated"),
    (Cow.STAGE_PREGNANT, "Pregnant"),
    (Cow.STAGE_NEARING_CALVING, "Nearing calving"),
    (Cow.STAGE_ACTIVE_LABOR, "Active labor"),
    (Cow.STAGE_POST_CALVING, "Post-calving"),
]

TRACKING_STEP_DESCRIPTIONS = {
    Cow.STAGE_REGISTERED: "Cow profile created and waiting for the next reproductive step.",
    Cow.STAGE_INSEMINATED: "Service happened and the next follow-up should stay visible.",
    Cow.STAGE_PREGNANT: "Pregnancy confirmed and calving planning should continue.",
    Cow.STAGE_NEARING_CALVING: "Calving window is close and the cow needs more watch.",
    Cow.STAGE_ACTIVE_LABOR: "Active labour has started and progress needs monitoring.",
    Cow.STAGE_POST_CALVING: "Calving completed and the cow moves into follow-up.",
}

# Keep reproductive timing assumptions centralized for consistent date guidance.
GESTATION_LENGTH_BY_BREED = {
    Cow.BREED_FRIESIAN: 279,
    Cow.BREED_AYRSHIRE: 280,
    Cow.BREED_JERSEY: 279,
    Cow.BREED_GUERNSEY: 285,
    Cow.BREED_SAHIWAL: 283,
    Cow.BREED_CROSSBREED: 283,
    Cow.BREED_OTHER: 283,
}

EVENT_STYLE_MAP = {
    ReproductiveEvent.EVENT_HEAT_OBSERVED: {
        "tone": "orange",
        "short_label": "Heat",
        "detail": "Heat observed and service timing can be planned from this day.",
    },
    ReproductiveEvent.EVENT_INSEMINATION_RECORDED: {
        "tone": "sky",
        "short_label": "AI",
        "detail": "Insemination recorded and follow-up predictions updated from this date.",
    },
    ReproductiveEvent.EVENT_PREGNANCY_CONFIRMED: {
        "tone": "emerald",
        "short_label": "OK",
        "detail": "Pregnancy confirmed and calving planning continues from here.",
    },
    ReproductiveEvent.EVENT_PREGNANCY_NOT_KEPT: {
        "tone": "rose",
        "short_label": "Loss",
        "detail": "Pregnancy did not continue and the cow returns to a watch-for-heat path.",
    },
    ReproductiveEvent.EVENT_CALVED: {
        "tone": "amber",
        "short_label": "Calved",
        "detail": "Calving recorded and the tracker moves into recovery follow-up.",
    },
}


def _sync_tracking_stage(cow):
    if cow.tracking_stage == Cow.STAGE_ACTIVE_LABOR:
        cow.is_pregnant = True
        return
    if cow.tracking_stage == Cow.STAGE_NEARING_CALVING:
        cow.is_pregnant = True
        return
    if cow.tracking_stage == Cow.STAGE_PREGNANT:
        cow.is_pregnant = True
        return
    if cow.tracking_stage in {Cow.STAGE_POST_CALVING, Cow.STAGE_REGISTERED, Cow.STAGE_INSEMINATED}:
        cow.is_pregnant = False


def _apply_default_tracking_stage(cow):
    # Guided registration chooses the first reproductive path, then we map it
    # into the current tracker stages so the rest of the farmer workflow stays
    # stable while reproductive event and support workflows are built out.
    if cow.reproductive_status == Cow.REPRODUCTIVE_STATUS_NOT_INSEMINATED:
        cow.tracking_stage = Cow.STAGE_REGISTERED
        cow.is_pregnant = False
    elif cow.reproductive_status == Cow.REPRODUCTIVE_STATUS_INSEMINATED:
        cow.tracking_stage = Cow.STAGE_INSEMINATED
        cow.is_pregnant = False
    elif cow.reproductive_status == Cow.REPRODUCTIVE_STATUS_PREGNANCY_CONFIRMED:
        cow.tracking_stage = Cow.STAGE_PREGNANT
        cow.is_pregnant = True
    elif cow.reproductive_status == Cow.REPRODUCTIVE_STATUS_NEAR_CALVING:
        cow.tracking_stage = Cow.STAGE_NEARING_CALVING
        cow.is_pregnant = True
    elif cow.expected_calving_date and cow.is_nearing_calving():
        cow.tracking_stage = Cow.STAGE_NEARING_CALVING
    elif cow.is_pregnant:
        cow.tracking_stage = Cow.STAGE_PREGNANT
    else:
        cow.tracking_stage = Cow.STAGE_REGISTERED
    _sync_tracking_stage(cow)


def _build_insemination_request_note(cow):
    note_parts = []
    if cow.last_heat_date:
        note_parts.append(f"Last heat observed on {cow.last_heat_date:%d %b %Y}.")
    if cow.insemination_type:
        note_parts.append(
            f"Preferred service type: {cow.get_insemination_type_display()}."
        )
    note_parts.append("Created from the farmer cow registration workflow.")
    return " ".join(note_parts)


def _ensure_open_insemination_request(cow):
    if cow.reproductive_status != Cow.REPRODUCTIVE_STATUS_NOT_INSEMINATED:
        return None

    active_request = cow.active_insemination_request
    if active_request:
        return active_request

    request = InseminationRequest.objects.create(
        cow=cow,
        farmer=cow.owner,
        service_type=cow.insemination_type,
        request_note=_build_insemination_request_note(cow),
    )
    # Keep the cached property aligned for the current request cycle so the same
    # response can render the new status without reloading the cow from the DB.
    cow.__dict__["active_insemination_request"] = request
    return request


def _resolve_active_insemination_request(cow):
    active_request = cow.active_insemination_request
    if not active_request:
        return

    active_request.status = InseminationRequest.STATUS_COMPLETED
    active_request.resolved_at = timezone.now()
    active_request.save(update_fields=["status", "resolved_at", "updated_at"])
    cow.__dict__["active_insemination_request"] = None


def _build_tracking_redirect(cow_id):
    return reverse("farmers_dashboard:cow_tracking", args=[cow_id])


def _derive_expected_calving_date(cow):
    if cow.expected_calving_date:
        return cow.expected_calving_date
    if not cow.insemination_date:
        return None
    gestation_days = GESTATION_LENGTH_BY_BREED.get(cow.breed, 283)
    return cow.insemination_date + timedelta(days=gestation_days)


def _save_reproductive_event(cow, *, recorded_by, event_type, event_date, notes=""):
    event = ReproductiveEvent.objects.create(
        cow=cow,
        recorded_by=recorded_by,
        event_type=event_type,
        event_date=event_date,
        notes=notes,
    )

    # The cow row stores the active state for the current cycle while the
    # The event table preserves the complete reproductive history for the activity list.
    if event_type == ReproductiveEvent.EVENT_HEAT_OBSERVED:
        cow.last_heat_date = event_date
        cow.insemination_date = None
        cow.pregnancy_confirmation_date = None
        cow.expected_calving_date = None
        cow.reproductive_status = Cow.REPRODUCTIVE_STATUS_NOT_INSEMINATED
        cow.tracking_stage = Cow.STAGE_REGISTERED
        cow.is_pregnant = False
        cow.needs_attention = False
        cow.attention_reason = ""
    elif event_type == ReproductiveEvent.EVENT_INSEMINATION_RECORDED:
        cow.insemination_date = event_date
        cow.pregnancy_confirmation_date = None
        cow.expected_calving_date = event_date + timedelta(
            days=GESTATION_LENGTH_BY_BREED.get(cow.breed, 283)
        )
        cow.reproductive_status = Cow.REPRODUCTIVE_STATUS_INSEMINATED
        cow.tracking_stage = Cow.STAGE_INSEMINATED
        cow.is_pregnant = False
        cow.needs_attention = False
        cow.attention_reason = ""
        _resolve_active_insemination_request(cow)
    elif event_type == ReproductiveEvent.EVENT_PREGNANCY_CONFIRMED:
        cow.pregnancy_confirmation_date = event_date
        cow.expected_calving_date = _derive_expected_calving_date(cow)
        cow.is_pregnant = True
        if cow.expected_calving_date and (cow.expected_calving_date - event_date).days <= 30:
            cow.reproductive_status = Cow.REPRODUCTIVE_STATUS_NEAR_CALVING
            cow.tracking_stage = Cow.STAGE_NEARING_CALVING
        else:
            cow.reproductive_status = Cow.REPRODUCTIVE_STATUS_PREGNANCY_CONFIRMED
            cow.tracking_stage = Cow.STAGE_PREGNANT
        cow.needs_attention = False
        cow.attention_reason = ""
    elif event_type == ReproductiveEvent.EVENT_PREGNANCY_NOT_KEPT:
        cow.insemination_date = None
        cow.pregnancy_confirmation_date = None
        cow.expected_calving_date = None
        cow.reproductive_status = Cow.REPRODUCTIVE_STATUS_NOT_INSEMINATED
        cow.tracking_stage = Cow.STAGE_REGISTERED
        cow.is_pregnant = False
        cow.needs_attention = True
        cow.attention_reason = "Pregnancy did not continue."
    elif event_type == ReproductiveEvent.EVENT_CALVED:
        cow.insemination_date = None
        cow.pregnancy_confirmation_date = None
        cow.expected_calving_date = None
        cow.reproductive_status = ""
        cow.tracking_stage = Cow.STAGE_POST_CALVING
        cow.is_pregnant = False
        cow.is_lactating = True
        cow.needs_attention = False
        cow.attention_reason = ""

    cow.save(
        update_fields=[
            "last_heat_date",
            "insemination_date",
            "pregnancy_confirmation_date",
            "expected_calving_date",
            "reproductive_status",
            "tracking_stage",
            "is_pregnant",
            "is_lactating",
            "needs_attention",
            "attention_reason",
            "updated_at",
        ]
    )
    return event


def _format_day_count(value, *, future_label, past_label):
    if value == 0:
        return "Today"
    if value > 0:
        return f"{value} day{'s' if value != 1 else ''} {future_label}"
    absolute = abs(value)
    return f"{absolute} day{'s' if absolute != 1 else ''} {past_label}"


def _build_tracking_timeline(cow):
    timeline_items = [
        {
            "label": "Cow registered",
            "date": timezone.localtime(cow.created_at).date(),
            "detail": "This cow profile was added to your herd tracker.",
        }
    ]

    if cow.last_heat_date:
        timeline_items.append(
            {
                "label": "Last heat",
                "date": cow.last_heat_date,
                "detail": "Used to keep service timing visible.",
            }
        )

    if cow.active_insemination_request:
        timeline_items.append(
            {
                "label": "Insemination requested",
                "date": timezone.localtime(cow.active_insemination_request.submitted_at).date(),
                "detail": "Support request created from this cow workflow.",
            }
        )

    if cow.insemination_date:
        timeline_items.append(
            {
                "label": "Insemination date",
                "date": cow.insemination_date,
                "detail": "Service date recorded for the tracker.",
            }
        )

    if cow.pregnancy_confirmation_date:
        timeline_items.append(
            {
                "label": "Pregnancy confirmation",
                "date": cow.pregnancy_confirmation_date,
                "detail": "Confirmation date saved for follow-up.",
            }
        )

    if cow.expected_calving_date:
        timeline_items.append(
            {
                "label": "Expected calving",
                "date": cow.expected_calving_date,
                "detail": "Use this date to plan the next check and calving watch.",
            }
        )

    return timeline_items


def _get_tracking_due_date(cow):
    return _derive_expected_calving_date(cow)


def _build_schedule_items(cow):
    today = timezone.localdate()
    items = []
    recorded_events = list(cow.reproductive_events.all())

    for event in recorded_events:
        style = EVENT_STYLE_MAP[event.event_type]
        items.append(
            {
                "kind": "point",
                "date": event.event_date,
                "end_date": event.event_date,
                "sort_date": event.event_date,
                "tone": style["tone"],
                "label": event.get_event_type_display(),
                "short_label": style["short_label"],
                "detail": event.notes or style["detail"],
                "priority": 100,
                "is_actual": True,
            }
        )

    due_date = _get_tracking_due_date(cow)

    if cow.last_heat_date and not cow.insemination_date:
        next_heat_start = cow.last_heat_date + timedelta(days=18)
        next_heat_end = cow.last_heat_date + timedelta(days=24)
        items.append(
            {
                "kind": "range",
                "date": next_heat_start,
                "end_date": next_heat_end,
                "sort_date": max(next_heat_start, today),
                "tone": "orange",
                "label": "Watch for next heat",
                "short_label": "Heat",
                "detail": f"Likely heat watch window from {next_heat_start:%d %b} to {next_heat_end:%d %b}.",
                "priority": 35,
                "is_actual": False,
            }
        )

    if cow.insemination_date:
        return_heat_start = cow.insemination_date + timedelta(days=18)
        return_heat_end = cow.insemination_date + timedelta(days=24)
        pregnancy_check_start = cow.insemination_date + timedelta(days=28)
        pregnancy_check_end = cow.insemination_date + timedelta(days=35)
        items.extend(
            [
                {
                    "kind": "range",
                    "date": return_heat_start,
                    "end_date": return_heat_end,
                    "sort_date": max(return_heat_start, today),
                    "tone": "orange",
                    "label": "Return-to-heat watch",
                    "short_label": "Heat",
                    "detail": f"Watch for a return to heat from {return_heat_start:%d %b} to {return_heat_end:%d %b}.",
                    "priority": 40,
                    "is_actual": False,
                },
                {
                    "kind": "range",
                    "date": pregnancy_check_start,
                    "end_date": pregnancy_check_end,
                    "sort_date": max(pregnancy_check_start, today),
                    "tone": "teal",
                    "label": "Pregnancy check window",
                    "short_label": "Check",
                    "detail": f"Best follow-up window from {pregnancy_check_start:%d %b} to {pregnancy_check_end:%d %b}.",
                    "priority": 50,
                    "is_actual": False,
                },
            ]
        )

    if due_date:
        close_up_start = due_date - timedelta(days=21)
        items.extend(
            [
                {
                    "kind": "range",
                    "date": close_up_start,
                    "end_date": due_date - timedelta(days=1),
                    "sort_date": max(close_up_start, today),
                    "tone": "amber",
                    "label": "Close-up calving watch",
                    "short_label": "Watch",
                    "detail": f"Closer calving watch from {close_up_start:%d %b} to {(due_date - timedelta(days=1)):%d %b}.",
                    "priority": 45,
                    "is_actual": False,
                },
                {
                    "kind": "point",
                    "date": due_date,
                    "end_date": due_date,
                    "sort_date": due_date,
                    "tone": "rose",
                    "label": "Expected calving day",
                    "short_label": "Due",
                    "detail": f"Expected calving day based on the current service timeline: {due_date:%d %b %Y}.",
                    "priority": 90,
                    "is_actual": False,
                },
            ]
        )
        if due_date < today and cow.tracking_stage != Cow.STAGE_POST_CALVING:
            items.append(
                {
                    "kind": "point",
                    "date": today,
                    "end_date": today,
                    "sort_date": today,
                    "tone": "rose",
                    "label": "Overdue for calving review",
                    "short_label": "Due",
                    "detail": "The expected calving day has passed. Keep this cow under closer watch or request support.",
                    "priority": 95,
                    "is_actual": False,
                }
            )

    return sorted(
        items,
        key=lambda item: (item["sort_date"], -item["priority"], item["label"]),
    )


def _build_tracking_history(cow):
    history_items = []
    for event in cow.reproductive_events.all()[:6]:
        style = EVENT_STYLE_MAP[event.event_type]
        history_items.append(
            {
                "label": event.get_event_type_display(),
                "date": event.event_date,
                "tone": style["tone"],
                "detail": event.notes or style["detail"],
            }
        )

    if history_items:
        return history_items

    return [
        {
            "label": "Cow registered",
            "date": timezone.localtime(cow.created_at).date(),
            "tone": "slate",
            "detail": "Registration started the tracking record for this cow.",
        }
    ]


def _build_upcoming_events(schedule_items):
    today = timezone.localdate()
    future_items = []

    for item in schedule_items:
        if item["end_date"] < today:
            continue

        display_date = max(item["date"], today)
        entry = {
            "label": item["label"],
            "date": display_date,
            "tone": item["tone"],
            "detail": item["detail"],
            "is_actual": item["is_actual"],
        }

        future_items.append(entry)

    deduped = []
    seen = set()
    for item in future_items:
        key = (item["label"], item["date"], item["detail"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    return {
        "items": deduped[:3],
    }


def _build_tracking_overview(cow):
    schedule_items = _build_schedule_items(cow)
    return {
        "upcoming_events": _build_upcoming_events(schedule_items),
        "history_items": _build_tracking_history(cow),
    }


def _build_stage_options(cow):
    current_index = next(
        (
            index
            for index, (value, _label) in enumerate(TRACKING_STEPS)
            if value == cow.tracking_stage
        ),
        0,
    )

    stage_options = []
    for index, (value, label) in enumerate(TRACKING_STEPS):
        if index < current_index:
            state = "completed"
        elif index == current_index:
            state = "current"
        elif index == current_index + 1:
            state = "next"
        else:
            state = "later"

        stage_options.append(
            {
                "value": value,
                "label": label,
                "description": TRACKING_STEP_DESCRIPTIONS[value],
                "state": state,
                "is_current": state == "current",
                "is_next": state == "next",
            }
        )

    return stage_options


def _get_cows_for_user(user):
    cows = list(
        Cow.objects.filter(owner=user)
        .prefetch_related(
            Prefetch(
                "insemination_requests",
                queryset=InseminationRequest.objects.order_by("-submitted_at"),
            )
        )
        .order_by(
            "-needs_attention",
            "expected_calving_date",
            "name",
        )
    )
    alerts = [
        cow
        for cow in cows
        if cow.needs_attention
        or cow.tracking_stage == Cow.STAGE_ACTIVE_LABOR
        or cow.is_nearing_calving()
    ]
    # Active labor must stay at the top, followed by manually flagged cows.
    alerts.sort(
        key=lambda cow: (
            cow.tracking_stage != Cow.STAGE_ACTIVE_LABOR,
            not cow.needs_attention,
            cow.expected_calving_date is None,
            cow.expected_calving_date or timezone.localdate(),
            cow.name.casefold(),
        )
    )
    follow_up = [cow for cow in cows if cow.expected_calving_date or cow.is_pregnant]
    return cows, alerts, follow_up


def _build_navigation_sections(
    total_cows,
    alert_count,
    unread_message_count,
    unread_notification_count,
    has_farm_location,
):
    return [
        {
            "label": "Main",
            "items": [
                {
                    "label": "Overview",
                    "url": reverse("farmers_dashboard:dashboard"),
                    "view_name": "farmers_dashboard:dashboard",
                    "icon": "overview",
                },
                {
                    "label": "My herd",
                    "url": reverse("farmers_dashboard:herd"),
                    "view_name": "farmers_dashboard:herd",
                    "icon": "herd",
                    "badge": str(total_cows) if total_cows else None,
                },
                {
                    "label": "Milk records",
                    "url": reverse("farmers_dashboard:milk_records"),
                    "view_name": "farmers_dashboard:milk_records",
                    "icon": "reports",
                },
                {
                    "label": "Alerts",
                    "url": reverse("farmers_dashboard:alerts"),
                    "view_name": "farmers_dashboard:alerts",
                    "icon": "alerts",
                    "badge": str(alert_count) if alert_count else None,
                },
                {
                    "label": "Service finder",
                    "url": reverse("farmers_dashboard:service_finder"),
                    "view_name": "farmers_dashboard:service_finder",
                    "icon": "services",
                },
                {
                    "label": "Messages",
                    "url": reverse("farmers_dashboard:messages"),
                    "view_name": "farmers_dashboard:messages",
                    "icon": "messages",
                    "badge": str(unread_message_count) if unread_message_count else None,
                },
                {
                    "label": "Notifications",
                    "url": reverse("farmers_dashboard:notifications"),
                    "view_name": "farmers_dashboard:notifications",
                    "icon": "notifications",
                    "badge": str(unread_notification_count)
                    if unread_notification_count
                    else None,
                },
            ],
        },
        {
            "label": "Farm",
            "items": [
                {
                    "label": "Farm location",
                    "url": reverse("farmers_dashboard:location"),
                    "view_name": "farmers_dashboard:location",
                    "icon": "location",
                    "badge": "Saved" if has_farm_location else None,
                },
                {
                    "label": "Reports",
                    "url": reverse("farmers_dashboard:reports"),
                    "view_name": "farmers_dashboard:reports",
                    "icon": "reports",
                },
            ],
        },
    ]


def _build_farmer_workspace_menu_sections():
    return [
        {
            "label": "Workspace",
            "items": [
                {
                    "label": "Profile details",
                    "description": "Review farm and account information.",
                    "url": reverse("users:profile"),
                },
                {
                    "label": "Update farm profile",
                    "description": "Keep the farm contact details ready.",
                    "url": reverse("users:profile_edit"),
                },
            ],
        },
        {
            "label": "Support",
            "items": [
                {
                    "label": "Ask AI",
                    "description": "Open quick guidance when you are stuck.",
                    "url": reverse("cow_calving_ai:index"),
                },
                {
                    "label": "Find a vet",
                    "description": "Open nearby veterinary help for urgent issues.",
                    "url": reverse("farmers_dashboard:service_finder"),
                },
                {
                    "label": "Set farm location",
                    "description": "Pin your farm so the veterinary team can route there.",
                    "url": reverse("farmers_dashboard:location"),
                },
            ],
        },
    ]


def _build_profile_readiness(user, profile):
    readiness_items = [
        {
            "label": "Display name",
            "value": user.get_full_name() or user.username,
            "is_complete": bool(user.get_full_name() or user.username),
        },
        {
            "label": "Email address",
            "value": user.email or "Add an email address",
            "is_complete": bool(user.email),
        },
        {
            "label": "Farm name",
            "value": profile.farm_name or "Add your farm name",
            "is_complete": bool(profile.farm_name),
        },
        {
            "label": "Phone number",
            "value": profile.phone_number or "Add a phone number",
            "is_complete": bool(profile.phone_number),
        },
    ]
    completed_items = sum(item["is_complete"] for item in readiness_items)
    readiness_percent = int((completed_items / len(readiness_items)) * 100)
    return readiness_items, readiness_percent


def _build_summary_cards(cows, alerts):
    total_cows = len(cows)
    pregnant_count = sum(1 for cow in cows if cow.is_pregnant)
    due_this_month_count = sum(1 for cow in cows if cow.is_due_this_month())
    pregnant_percent = int((pregnant_count / total_cows) * 100) if total_cows else 0
    return [
        {
            "label": "Total herd",
            "value": str(total_cows),
            "badge": "+ this month" if total_cows else "Start herd",
            "tone": "sky",
        },
        {
            "label": "Pregnant",
            "value": str(pregnant_count),
            "badge": f"{pregnant_percent}% herd" if total_cows else "No records",
            "tone": "emerald",
        },
        {
            "label": "Due this month",
            "value": str(due_this_month_count),
            "badge": "Calving watch",
            "tone": "amber",
        },
        {
            "label": "Active alerts",
            "value": str(len(alerts)),
            "badge": f"{len(alerts)} open" if alerts else "All quiet",
            "tone": "rose",
        },
    ]


def _build_follow_up_schedule_rows(cows):
    today = timezone.localdate()
    rows = []

    for cow in cows:
        if cow.expected_calving_date:
            next_date = cow.expected_calving_date
            next_label = "Expected calving"
            if cow.is_nearing_calving():
                detail = "Calving window is close. Keep this cow under closer watch."
            else:
                detail = "Keep this date visible so calving preparation stays on time."
        elif cow.insemination_date:
            next_date = cow.insemination_date + timedelta(days=28)
            next_label = "Pregnancy check"
            detail = "Check the cow around this date to confirm whether the service held."
        elif cow.pregnancy_confirmation_date:
            next_date = cow.pregnancy_confirmation_date
            next_label = "Pregnancy confirmed"
            detail = "Pregnancy is recorded. Add or confirm the calving timeline next."
        else:
            continue

        day_delta = (next_date - today).days
        rows.append(
            {
                "cow": cow,
                "next_label": next_label,
                "next_date": next_date,
                "next_timing": _format_day_count(
                    day_delta,
                    future_label="to follow-up",
                    past_label="since follow-up",
                ),
                "detail": detail,
            }
        )

    return sorted(rows, key=lambda item: item["next_date"])


def _matches_farmer_search(text_parts, query):
    haystack = " ".join(str(part or "").lower() for part in text_parts)
    return query in haystack


def _build_quick_links():
    return [
        {
            "label": "Ask AI",
            "description": "Use quick guidance when the next action is unclear.",
            "url": reverse("cow_calving_ai:index"),
        },
        {
            "label": "Find a vet",
            "description": "Open nearby veterinary support for urgent cases.",
            "url": reverse("farmers_dashboard:service_finder"),
        },
        {
            "label": "Warning signs",
            "description": "Open the guide troubleshooting section for urgent warning signs.",
            "url": f"{reverse('Core_Web:guide')}#trouble",
        },
    ]


def _build_farmer_overview_quick_actions():
    return [
        {
            "label": "Add Cow",
            "description": "Register a new herd entry.",
            "url": reverse("farmers_dashboard:cow_register"),
            "icon": "plus",
        },
        {
            "label": "Open Herd",
            "description": "Review all registered cows.",
            "url": reverse("farmers_dashboard:herd"),
            "icon": "herd",
        },
        {
            "label": "Find Provider",
            "description": "Open veterinary and AI support.",
            "url": reverse("farmers_dashboard:service_finder"),
            "icon": "provider",
        },
        {
            "label": "Open Alerts",
            "description": "Review cows needing attention.",
            "url": reverse("farmers_dashboard:alerts"),
            "icon": "alerts",
        },
    ]


def _build_farmer_overview_support_items(profile, unread_message_count):
    message_detail = "Continue provider conversations."
    if unread_message_count:
        plural = "s" if unread_message_count != 1 else ""
        message_detail = f"{unread_message_count} unread message update{plural}."

    return [
        {
            "label": "Service finder",
            "description": "Browse veterinary and AI support for the next farm task.",
            "meta": "Open directory",
            "url": reverse("farmers_dashboard:service_finder"),
        },
        {
            "label": "Messages",
            "description": message_detail,
            "meta": "Open inbox",
            "url": reverse("farmers_dashboard:messages"),
        },
        {
            "label": "Farm location",
            "description": (
                "Farm pin saved and ready for routing."
                if profile.has_farm_location
                else "Pin the farm so providers can route there faster."
            ),
            "meta": "Saved" if profile.has_farm_location else "Setup",
            "url": reverse("farmers_dashboard:location"),
        },
    ]


def _extract_service_finder_filters(source):
    valid_counties = {value for value, _label in KENYA_COUNTY_OPTIONS}
    valid_service_types = {value for value, _label in SERVICE_TYPE_OPTIONS}
    selected_county = source.get("county", "").strip()
    selected_service_type = source.get("service_type", "").strip()

    if selected_county not in valid_counties:
        selected_county = ""
    if selected_service_type not in valid_service_types:
        selected_service_type = ""

    return selected_county, selected_service_type


def _get_service_provider(provider_key):
    if not provider_key:
        return None
    return next(
        (
            provider
            for provider in _build_service_provider_directory()
            if provider["key"] == provider_key
        ),
        None,
    )


def _build_registered_veterinary_directory():
    providers = []
    for user in get_veterinary_users():
        profile = getattr(user, "profile", None)
        display_name = user.get_full_name().strip() or user.username
        phone_number = (getattr(profile, "phone_number", "") or "").strip()
        professional_id = (getattr(profile, "professional_id", "") or "").strip()
        title_suffix = (
            f" • {professional_id}" if professional_id else ""
        )
        providers.append(
            {
                "key": f"registered-veterinary-{user.pk}",
                "name": display_name,
                "provider_title": f"Registered veterinary account{title_suffix}",
                "county": "",
                "county_label": "Registered on CowCalving",
                "service_type": SERVICE_TYPE_VETERINARY,
                "service_type_label": "Veterinary",
                "summary": "Live veterinary account ready to receive farmer messages inside the workspace during the demo.",
                "phone": phone_number or "Available in the dashboard inbox",
                "email": user.email or "Account email not shared",
                "coverage": "Messages route directly to this veterinary workspace account.",
                "availability": "Active account",
                "is_verified": True,
                "is_registered_account": True,
                "is_demo_profile": False,
                "status_badge": "Active account",
                # The service finder uses this to route the message thread into
                # the actual veterinary dashboard account instead of a demo-only
                # listing.
                "assigned_veterinary_user": user,
                "sort_priority": 0,
            }
        )
    return providers


def _build_service_provider_directory():
    # Keep live veterinary accounts first so presentation demos use real inboxes
    # before falling back to the static sample directory.
    registered_providers = _build_registered_veterinary_directory()
    registered_emails = {
        provider["email"].strip().lower()
        for provider in registered_providers
        if provider.get("email")
    }
    registered_names = {
        provider["name"].strip().lower() for provider in registered_providers
    }

    demo_providers = []
    for provider in SERVICE_PROVIDER_DIRECTORY:
        provider_copy = provider.copy()
        email = provider_copy.get("email", "").strip().lower()
        name = provider_copy.get("name", "").strip().lower()
        if email in registered_emails or name in registered_names:
            continue
        provider_copy["is_registered_account"] = False
        provider_copy["is_demo_profile"] = True
        provider_copy["status_badge"] = (
            "Demo profile"
            if provider_copy["service_type"] == SERVICE_TYPE_VETERINARY
            else "Demo listing"
        )
        provider_copy["sort_priority"] = (
            1
            if provider_copy["service_type"] == SERVICE_TYPE_VETERINARY
            else 2
        )
        demo_providers.append(provider_copy)

    providers = registered_providers + demo_providers
    providers.sort(key=lambda provider: (provider["sort_priority"], provider["name"].lower()))
    return providers


def _build_service_finder_context(
    request,
    *,
    filter_source=None,
    active_provider_key="",
    active_panel="",
    message_form=None,
):
    selected_county, selected_service_type = _extract_service_finder_filters(
        filter_source or request.GET
    )

    providers = [provider.copy() for provider in _build_service_provider_directory()]
    if selected_county:
        providers = [
            provider for provider in providers if provider["county"] == selected_county
        ]
    if selected_service_type:
        providers = [
            provider
            for provider in providers
            if provider["service_type"] == selected_service_type
        ]

    active_provider = None
    if active_provider_key:
        active_provider = next(
            (provider for provider in providers if provider["key"] == active_provider_key),
            None,
        )
        if not active_provider:
            active_provider_key = ""
            active_panel = ""

    if active_panel not in {"profile", "message"}:
        active_panel = ""

    if active_panel == "message" and active_provider and message_form is None:
        message_form = ServiceProviderMessageForm(
            initial={
                "provider_key": active_provider["key"],
                "county": selected_county,
                "service_type": selected_service_type,
            }
        )

    return {
        "selected_county": selected_county,
        "selected_service_type": selected_service_type,
        "county_options": [{"value": "", "label": "All counties"}]
        + [{"value": value, "label": label} for value, label in KENYA_COUNTY_OPTIONS],
        "service_type_options": [{"value": "", "label": "All types"}]
        + [
            {"value": value, "label": label}
            for value, label in SERVICE_TYPE_OPTIONS
        ],
        "service_providers": providers,
        "service_provider_count": len(providers),
        "service_directory_count": len(SERVICE_PROVIDER_DIRECTORY),
        "active_provider_key": active_provider_key,
        "active_provider_panel": active_panel,
        "active_provider": active_provider,
        "message_form": message_form,
    }


def _build_farmer_dashboard_context(
    request,
    *,
    page_title,
    page_eyebrow,
    page_heading,
    page_intro,
    page_header_title=None,
    page_header_context=None,
    header_primary_action=None,
    extra_context=None,
):
    profile = get_profile(request.user)
    display_name = request.user.get_full_name().strip() or request.user.username
    initials = "".join(part[0].upper() for part in display_name.split()[:2] if part) or "FM"
    cows, alerts, follow_up_items = _get_cows_for_user(request.user)
    readiness_items, readiness_percent = _build_profile_readiness(request.user, profile)
    unread_message_count = get_unread_thread_count(request.user)
    unread_notification_count = get_unread_notification_count(request.user)
    context = {
        "dashboard_home_url": reverse("farmers_dashboard:dashboard"),
        "back_to_website_url": reverse("Core_Web:home"),
        "ai_workspace_url": reverse("cow_calving_ai:index"),
        "ai_workspace_embed_url": f"{reverse('cow_calving_ai:index')}?embedded=1",
        "profile": profile,
        "display_name": display_name,
        "farmer_initials": initials,
        "page_title": page_title,
        "page_eyebrow": page_eyebrow,
        "page_heading": page_heading,
        "page_intro": page_intro,
        "page_header_title": page_header_title or page_heading,
        "page_header_context": page_header_context,
        "dashboard_search_query": request.GET.get("q", "").strip(),
        "navigation_sections": _build_navigation_sections(
            len(cows),
            len(alerts),
            unread_message_count,
            unread_notification_count,
            profile.has_farm_location,
        ),
        "workspace_menu_sections": _build_farmer_workspace_menu_sections(),
        "profile_readiness_items": readiness_items,
        "profile_readiness_percent": readiness_percent,
        "summary_cards": _build_summary_cards(cows, alerts),
        "cow_records": cows,
        "cow_alerts": alerts,
        "follow_up_items": follow_up_items,
        "dashboard_quick_links": _build_quick_links(),
        "unread_message_count": unread_message_count,
        "unread_notification_count": unread_notification_count,
        "header_primary_action": header_primary_action
        or {
            "label": "Register cow",
            "url": reverse("farmers_dashboard:cow_register"),
        },
    }
    if extra_context:
        context.update(extra_context)
    return context


def _build_farmer_search_results(user, query):
    normalized_query = query.strip().lower()
    cows, alerts, _follow_up = _get_cows_for_user(user)
    providers = _build_service_provider_directory()

    if not normalized_query:
        return {
            "matching_cows": [],
            "matching_alerts": [],
            "matching_providers": [],
        }

    matching_cows = [
        cow
        for cow in cows
        if _matches_farmer_search(
            [
                cow.name,
                cow.cow_number,
                cow.get_breed_display(),
                cow.status_label,
                cow.summary_text,
                cow.next_action_text,
            ],
            normalized_query,
        )
    ]

    matching_alerts = [
        cow
        for cow in alerts
        if _matches_farmer_search(
            [
                cow.name,
                cow.cow_number,
                cow.alert_category,
                cow.summary_text,
                cow.next_action_text,
            ],
            normalized_query,
        )
    ]

    matching_providers = [
        provider
        for provider in providers
        if _matches_farmer_search(
            [
                provider["name"],
                provider["provider_title"],
                provider["service_type_label"],
                provider["county_label"],
                provider["summary"],
                provider["coverage"],
            ],
            normalized_query,
        )
    ]

    return {
        "matching_cows": matching_cows[:8],
        "matching_alerts": matching_alerts[:6],
        "matching_providers": matching_providers[:6],
    }


def _build_location_initial_state(profile):
    if profile.has_farm_location:
        return {
            "lat": float(profile.farm_latitude),
            "lng": float(profile.farm_longitude),
            "zoom": 13,
            "source": profile.farm_location_source or "manual_pin",
        }
    return {
        "lat": KENYA_MAP_CENTER["lat"],
        "lng": KENYA_MAP_CENTER["lng"],
        "zoom": 6,
        "source": "manual_pin",
    }


@login_required
@role_required("farmer")
def dashboard_view(request):
    context = _build_farmer_dashboard_context(
        request,
        page_title="Farmer Dashboard | CowCalving",
        page_eyebrow="Farmer workspace",
        page_heading="Herd overview",
        page_intro="Register cows, upload a photo, and start tracking calving from one place.",
        page_header_context="Interactive herd dashboard",
    )
    context["milk_drop_alerts"] = MilkProductionAlert.objects.filter(
        cow__owner=request.user,
        status=MilkProductionAlert.STATUS_ACTIVE,
    ).select_related("cow")[:5]
    milk_drop_alert_count = MilkProductionAlert.objects.filter(
        cow__owner=request.user,
        status=MilkProductionAlert.STATUS_ACTIVE,
    ).count()
    active_alert_card = context["summary_cards"][-1]
    active_alert_count = int(active_alert_card["value"]) + milk_drop_alert_count
    active_alert_card["value"] = str(active_alert_count)
    active_alert_card["badge"] = (
        f"{active_alert_count} open" if active_alert_count else "All quiet"
    )
    # Keep the overview intentionally light: a short action row, a short herd
    # list, and a short support section instead of repeating every deep page.
    context["overview_quick_actions"] = _build_farmer_overview_quick_actions()
    context["overview_support_items"] = _build_farmer_overview_support_items(
        context["profile"],
        context["unread_message_count"],
    )
    context["follow_up_rows"] = _build_follow_up_schedule_rows(
        context["follow_up_items"]
    )[:3]
    return render(request, "farmers_dashboard/dashboard.html", context)


@login_required
@role_required("farmer")
def search_view(request):
    query = request.GET.get("q", "").strip()
    results = _build_farmer_search_results(request.user, query)
    total_results = (
        len(results["matching_cows"])
        + len(results["matching_alerts"])
        + len(results["matching_providers"])
    )
    return render(
        request,
        "farmers_dashboard/search_results.html",
        _build_farmer_dashboard_context(
            request,
            page_title="Farmer Search | CowCalving",
            page_eyebrow="Search",
            page_heading="Search results",
            page_intro="Find cows, alerts, and service support from one search.",
            page_header_context="Dashboard search",
            header_primary_action={
                "label": "Back to overview",
                "url": reverse("farmers_dashboard:dashboard"),
            },
            extra_context={
                "search_query": query,
                "search_results_total": total_results,
                **results,
            },
        ),
    )


@login_required
@role_required("farmer")
def herd_view(request):
    context = _build_farmer_dashboard_context(
        request,
        page_title="My Herd | CowCalving",
        page_eyebrow="Herd dashboard",
        page_heading="My cows",
        page_intro="Find a cow by name or tag, then open her record.",
        header_primary_action={
            "label": "Add cow",
            "url": reverse("farmers_dashboard:cow_register"),
        },
    )
    all_cows = context["cow_records"]
    query = request.GET.get("q", "").strip()
    matching_cows = all_cows
    if query:
        normalized_query = query.casefold()
        matching_cows = [
            cow
            for cow in all_cows
            if normalized_query in cow.name.casefold()
            or normalized_query in cow.cow_number.casefold()
        ]

    context.update(
        {
            "herd_page": Paginator(matching_cows, 24).get_page(
                request.GET.get("page")
            ),
            "herd_search_query": query,
            "herd_total_count": len(all_cows),
            "herd_result_count": len(matching_cows),
        }
    )
    return render(
        request,
        "farmers_dashboard/herd.html",
        context,
    )


@login_required
@role_required("farmer")
def milk_records_view(request, record_id=None):
    editing_record = None
    if record_id is not None:
        editing_record = get_object_or_404(
            MilkRecord.objects.select_related("cow"),
            pk=record_id,
            cow__owner=request.user,
        )
    selected_cow = editing_record.cow if editing_record else None
    selected_cow_id = request.GET.get("cow")
    if selected_cow is None and selected_cow_id:
        selected_cow = get_object_or_404(
            Cow,
            owner=request.user,
            pk=selected_cow_id,
        )

    if request.method == "POST":
        form = MilkRecordForm(
            request.POST,
            instance=editing_record,
            farmer=request.user,
        )
        if form.is_valid():
            with transaction.atomic():
                record = form.save()
                recalculate_milk_alerts(record.cow, record.record_date)
            action = "updated" if editing_record else "saved"
            messages.success(
                request,
                f"Milk record for {record.cow.name} on {record.record_date:%d %b %Y} {action}; daily total {record.daily_yield_liters:.2f} L.",
            )
            milk_alert = MilkProductionAlert.objects.filter(
                cow=record.cow,
                record_date=record.record_date,
                status=MilkProductionAlert.STATUS_ACTIVE,
            ).first()
            if milk_alert:
                messages.warning(
                    request,
                    f"Milk is down {milk_alert.drop_percent:.0f}% for {record.cow.name}. Open Cow alerts to see the suggested check.",
                )
            return redirect(f"{reverse('farmers_dashboard:milk_records')}?cow={record.cow_id}")
    else:
        initial = None
        if editing_record is None:
            initial = {"record_date": timezone.localdate()}
            if selected_cow:
                initial["cow"] = selected_cow.pk
        form = MilkRecordForm(
            instance=editing_record,
            initial=initial,
            farmer=request.user,
        )

    records = MilkRecord.objects.filter(cow__owner=request.user).select_related("cow")
    if selected_cow:
        records = records.filter(cow=selected_cow)
    records_page = Paginator(records, 20).get_page(request.GET.get("page"))
    milk_guide_average = None
    if selected_cow and records_page.paginator.count >= 7:
        # Use the seven latest recorded days; missing calendar dates are not zero-yield days.
        recent_yields = records.order_by("-record_date").values_list(
            "daily_yield_liters", flat=True
        )[:7]
        milk_guide_average = sum(recent_yields, Decimal("0")) / Decimal("7")
    history_cows = []
    if selected_cow is None:
        history_cows = list(
            Cow.objects.filter(owner=request.user)
            .annotate(milk_record_count=Count("milk_records"))
            .prefetch_related(
                Prefetch(
                    "milk_records",
                    queryset=MilkRecord.objects.order_by("-record_date")[:5],
                    to_attr="recent_milk_entries",
                )
            )
            .order_by("name", "cow_number")
        )
    page_heading = (
        f"Milk records for {selected_cow.name}" if selected_cow else "Milk records"
    )
    return render(
        request,
        "farmers_dashboard/milk_records.html",
        _build_farmer_dashboard_context(
            request,
            page_title=f"{page_heading} | CowCalving",
            page_eyebrow="Milk production",
            page_heading=page_heading,
            page_intro=(
                f"Record {selected_cow.name}'s morning and evening milk, then review the daily total."
                if selected_cow
                else "Record each cow's morning and evening milk, then review or correct the calculated daily total."
            ),
            header_primary_action={
                "label": "Open cow" if selected_cow else "My herd",
                "url": (
                    reverse("farmers_dashboard:cow_tracking", args=[selected_cow.pk])
                    if selected_cow
                    else reverse("farmers_dashboard:herd")
                ),
            },
            extra_context={
                "milk_form": form,
                "milk_records_page": records_page,
                "milk_history_cows": history_cows,
                "editing_record": editing_record,
                "selected_cow": selected_cow,
                "milk_guide_average": milk_guide_average,
                "milk_guide_missing_records": max(
                    0, 7 - records_page.paginator.count
                ),
            },
        ),
    )


@login_required
@role_required("farmer")
def alerts_view(request):
    context = _build_farmer_dashboard_context(
        request,
        page_title="Cow Alerts | CowCalving",
        page_eyebrow="Alerts",
        page_heading="Cow alerts",
        page_intro="See cows with issues or those nearing calving, then open the next step.",
        header_primary_action={
            "label": "Open herd",
            "url": reverse("farmers_dashboard:herd"),
        },
    )
    search_query = request.GET.get("q", "").strip()
    cow_alerts = context["cow_alerts"]
    milk_drop_alerts = list(MilkProductionAlert.objects.filter(
        cow__owner=request.user,
        status__in=[
            MilkProductionAlert.STATUS_ACTIVE,
            MilkProductionAlert.STATUS_ACKNOWLEDGED,
        ],
    ).select_related("cow", "check_observation").order_by(
        Case(
            When(severity=MilkProductionAlert.SEVERITY_CRITICAL, then=0),
            default=1,
            output_field=IntegerField(),
        ),
        "-record_date",
    ))

    if search_query:
        normalized_query = search_query.casefold()
        cow_alerts = [
            cow
            for cow in cow_alerts
            if normalized_query in cow.name.casefold()
            or normalized_query in cow.cow_number.casefold()
            or normalized_query in cow.alert_reason_text.casefold()
            or normalized_query in cow.alert_label.casefold()
        ]
        milk_drop_alerts = [
            alert
            for alert in milk_drop_alerts
            if normalized_query in alert.cow.name.casefold()
            or normalized_query in alert.cow.cow_number.casefold()
            or normalized_query in alert.severity.casefold()
            or normalized_query in alert.next_step_text.casefold()
        ]

    for alert in milk_drop_alerts:
        alert.quick_check_form = MilkAlertCheckForm(
            instance=getattr(alert, "check_observation", None)
        )

    context["cow_alerts"] = cow_alerts
    context["milk_drop_alerts"] = milk_drop_alerts
    context["alert_counts"] = {
        "all": len(cow_alerts),
        "nearing_calving": sum(
            1 for cow in cow_alerts if cow.alert_category == "Nearing calving"
        ),
        "needs_attention": sum(1 for cow in cow_alerts if cow.needs_attention),
    }
    context["alerts_search_query"] = search_query
    context["hide_dashboard_search"] = True
    context["cow_check_count"] = len(cow_alerts)
    context["milk_drop_alert_count"] = len(milk_drop_alerts)
    context["total_alert_count"] = (
        context["cow_check_count"] + context["milk_drop_alert_count"]
    )
    return render(request, "farmers_dashboard/alerts.html", context)


@login_required
@role_required("farmer")
@require_POST
def acknowledge_milk_alert_view(request, alert_id):
    alert = get_object_or_404(
        MilkProductionAlert,
        pk=alert_id,
        cow__owner=request.user,
    )
    acknowledge_milk_alert(alert)
    messages.success(request, f"Follow-up for {alert.cow.name} marked as seen.")
    return redirect("farmers_dashboard:alerts")


@login_required
@role_required("farmer")
@require_POST
def record_milk_alert_check_view(request, alert_id):
    alert = get_object_or_404(
        MilkProductionAlert.objects.select_related("cow", "check_observation"),
        pk=alert_id,
        cow__owner=request.user,
    )
    check_form = MilkAlertCheckForm(
        request.POST,
        instance=getattr(alert, "check_observation", None),
    )
    if check_form.is_valid():
        check = check_form.save(commit=False)
        check.alert = alert
        if check.pk is None:
            check.recorded_by = request.user
        check.save()
        messages.success(
            request,
            f"Check-in for {alert.cow.name} saved to the cow's report.",
        )
    else:
        messages.error(
            request,
            "Choose Yes, No, or Not sure for each quick-check question.",
        )
    return redirect("farmers_dashboard:alerts")


@login_required
@role_required("farmer")
def reports_view(request):
    selected_cow_id = request.GET.get("cow", "").strip()
    selected_cow = None
    milk_report_records = []
    milk_report_average = None
    calvings_recorded = 0
    milk_alert_checks = []
    expected_calving_date = None
    calving_date_is_estimated = False
    expected_heat_window = None
    pregnancy_check_window = None
    calving_prep_window = None
    pregnancy_confirmed = False

    if selected_cow_id:
        selected_cow = get_object_or_404(
            Cow,
            owner=request.user,
            pk=selected_cow_id,
        )
        milk_report_records = list(
            selected_cow.milk_records.order_by("-record_date")[:7]
        )
        if milk_report_records:
            milk_report_average = sum(
                record.daily_yield_liters for record in milk_report_records
            ) / len(milk_report_records)
        # Count recorded calving events; do not imply an unlogged lifetime total.
        calvings_recorded = selected_cow.reproductive_events.filter(
            event_type=ReproductiveEvent.EVENT_CALVED
        ).count()
        pregnancy_confirmed = bool(
            selected_cow.is_pregnant
            or selected_cow.pregnancy_confirmation_date
            or selected_cow.tracking_stage
            in {Cow.STAGE_PREGNANT, Cow.STAGE_NEARING_CALVING}
        )
        expected_calving_date = _derive_expected_calving_date(selected_cow)
        calving_date_is_estimated = bool(
            expected_calving_date and not selected_cow.expected_calving_date
        )
        if pregnancy_confirmed and expected_calving_date:
            calving_prep_window = (
                expected_calving_date - timedelta(days=21),
                expected_calving_date - timedelta(days=1),
            )
        if not pregnancy_confirmed:
            heat_reference_date = (
                selected_cow.insemination_date or selected_cow.last_heat_date
            )
            if heat_reference_date:
                expected_heat_window = (
                    heat_reference_date + timedelta(days=18),
                    heat_reference_date + timedelta(days=24),
                )
            if selected_cow.insemination_date:
                pregnancy_check_window = (
                    selected_cow.insemination_date + timedelta(days=28),
                    selected_cow.insemination_date + timedelta(days=35),
                )
        milk_alert_checks = list(
            selected_cow.milk_production_alerts.filter(
                check_observation__isnull=False
            )
            .select_related("check_observation", "check_observation__recorded_by")
            .order_by("-check_observation__recorded_at", "-record_date")
        )

    context = _build_farmer_dashboard_context(
        request,
        page_title="Cow Reports | CowCalving",
        page_eyebrow="Reports",
        page_heading="Cow reports",
        page_intro=(
            f"A summary of {selected_cow.name}'s breeding dates, milk production, and follow-up checks."
            if selected_cow
            else "Browse each cow's key information and milk production."
        ),
        header_primary_action={
            "label": "Open cow" if selected_cow else "Open herd",
            "url": (
                reverse("farmers_dashboard:cow_tracking", args=[selected_cow.pk])
                if selected_cow
                else reverse("farmers_dashboard:herd")
            ),
        },
    )
    context.update(
        {
            "report_cows": Cow.objects.filter(owner=request.user).order_by(
                "name", "cow_number"
            ),
            "selected_cow": selected_cow,
            "milk_report_records": milk_report_records,
            "milk_report_average": milk_report_average,
            "milk_alert_checks": milk_alert_checks,
            "calvings_recorded": calvings_recorded,
            "expected_calving_date": expected_calving_date,
            "calving_date_is_estimated": calving_date_is_estimated,
            "expected_heat_window": expected_heat_window,
            "pregnancy_check_window": pregnancy_check_window,
            "calving_prep_window": calving_prep_window,
            "pregnancy_confirmed": pregnancy_confirmed,
            "report_generated_date": timezone.localdate(),
        }
    )
    return render(request, "farmers_dashboard/reports.html", context)


@login_required
@role_required("farmer")
def service_finder_view(request):
    if request.method == "POST" and request.POST.get("send_message"):
        message_form = ServiceProviderMessageForm(request.POST, request.FILES)
        active_provider_key = request.POST.get("provider_key", "").strip()
        if message_form.is_valid():
            provider = _get_service_provider(message_form.cleaned_data["provider_key"])
            if provider:
                # Keep provider contact details on the message record so the vet
                # workspace can read the exact same item even before providers
                # become first-class database users.
                ServiceProviderMessage.objects.create(
                    farmer=request.user,
                    provider_key=provider["key"],
                    provider_name=provider["name"],
                    provider_title=provider["provider_title"],
                    provider_service_type=provider["service_type"],
                    provider_county=provider["county_label"],
                    provider_phone=provider["phone"],
                    provider_email=provider["email"],
                    message=message_form.cleaned_data["message"],
                )
                thread = create_or_append_provider_thread(
                    farmer=request.user,
                    provider=provider,
                    body=message_form.cleaned_data["message"],
                    image=message_form.cleaned_data.get("image"),
                )
                messages.success(
                    request,
                    f"Message sent to {provider['name']}. The provider will see it in the workspace flow.",
                )
                return redirect("farmers_dashboard:messages_thread", thread_id=thread.pk)
            message_form.add_error(
                None,
                "This provider is no longer available in the directory. Choose another provider.",
            )

        extra_context = _build_service_finder_context(
            request,
            filter_source=request.POST,
            active_provider_key=active_provider_key,
            active_panel="message",
            message_form=message_form,
        )
    else:
        extra_context = _build_service_finder_context(
            request,
            active_provider_key=request.GET.get("provider", "").strip(),
            active_panel=request.GET.get("panel", "").strip(),
        )

    return render(
        request,
        "farmers_dashboard/service_finder.html",
        _build_farmer_dashboard_context(
            request,
            page_title="Service Finder | CowCalving",
            page_eyebrow="Farmer support",
            page_heading="Service finder",
            page_intro="Filter by county and provider type, open the provider profile, then send a short message when you are ready.",
            page_header_context="Find veterinary and AI support by county",
            header_primary_action={
                "label": "Reset filters",
                "url": reverse("farmers_dashboard:service_finder"),
            },
            extra_context=extra_context,
        ),
    )


def _build_thread_participants_for_farmer(thread):
    return {
        "title": thread.provider_name_snapshot,
        "subtitle": thread.provider_title_snapshot or "Service provider",
        "meta": thread.cow.name if thread.cow else "General support",
    }


def _get_provider_thread_for_farmer(farmer, provider_key):
    if not provider_key:
        return None
    return (
        ConversationThread.objects.filter(
            farmer=farmer,
            provider_key=provider_key,
        )
        .exclude(status=ConversationThread.STATUS_CLOSED)
        .order_by("-last_message_at", "-updated_at")
        .first()
    )


def _load_farmer_message_state(request, thread_id=None, preserve_empty_selection=False):
    selected_thread = None
    if thread_id is not None:
        selected_thread = get_thread_for_user(request.user, thread_id)
        if selected_thread is None:
            raise Http404("Conversation not found.")

    if selected_thread is not None:
        mark_thread_messages_read(selected_thread, request.user)

    thread_list = get_threads_for_user(request.user)
    if selected_thread is not None:
        selected_thread = next(
            (thread for thread in thread_list if thread.pk == selected_thread.pk),
            selected_thread,
        )
    elif not preserve_empty_selection and thread_list:
        selected_thread = thread_list[0]
    return thread_list, selected_thread


@login_required
@role_required("farmer")
def messages_view(request, thread_id=None):
    selected_thread = None
    compose_provider = None
    compose_form = None
    reply_form = ConversationReplyForm()
    compose_provider_key = request.GET.get("provider", "").strip()
    if thread_id is not None:
        selected_thread = get_thread_for_user(request.user, thread_id)
        if selected_thread is None:
            raise Http404("Conversation not found.")
    elif compose_provider_key:
        compose_provider = _get_service_provider(compose_provider_key)
        if compose_provider is None:
            raise Http404("Provider not found.")
        selected_thread = _get_provider_thread_for_farmer(
            request.user,
            compose_provider_key,
        )

    if request.method == "POST":
        if request.POST.get("start_conversation"):
            compose_form = ServiceProviderMessageForm(request.POST, request.FILES)
            if compose_form.is_valid():
                compose_provider = _get_service_provider(
                    compose_form.cleaned_data["provider_key"]
                )
                if compose_provider:
                    ServiceProviderMessage.objects.create(
                        farmer=request.user,
                        provider_key=compose_provider["key"],
                        provider_name=compose_provider["name"],
                        provider_title=compose_provider["provider_title"],
                        provider_service_type=compose_provider["service_type"],
                        provider_county=compose_provider["county_label"],
                        provider_phone=compose_provider["phone"],
                        provider_email=compose_provider["email"],
                        message=compose_form.cleaned_data["message"],
                    )
                    thread = create_or_append_provider_thread(
                        farmer=request.user,
                        provider=compose_provider,
                        body=compose_form.cleaned_data["message"],
                        image=compose_form.cleaned_data.get("image"),
                    )
                    messages.success(
                        request,
                        f"Message sent to {compose_provider['name']}.",
                    )
                    return redirect(
                        "farmers_dashboard:messages_thread",
                        thread_id=thread.pk,
                    )
                compose_form.add_error(
                    None,
                    "This provider is no longer available. Choose another provider.",
                )
        else:
            if selected_thread is None:
                raise Http404("Conversation not found.")
            reply_form = ConversationReplyForm(request.POST, request.FILES)
            if reply_form.is_valid():
                send_thread_message(
                    thread=selected_thread,
                    sender=request.user,
                    body=reply_form.cleaned_data["body"],
                    image=reply_form.cleaned_data.get("image"),
                )
                messages.success(request, "Your reply was sent.")
                return redirect("farmers_dashboard:messages_thread", thread_id=selected_thread.pk)
    # Keep the right panel in "new conversation" mode when the farmer came
    # from a provider card and no thread exists yet; otherwise the first old
    # thread would immediately replace the compose state.
    preserve_empty_selection = compose_provider is not None and selected_thread is None
    thread_list, selected_thread = _load_farmer_message_state(
        request,
        thread_id=selected_thread.pk if selected_thread else thread_id,
        preserve_empty_selection=preserve_empty_selection,
    )
    if compose_provider and selected_thread is not None:
        compose_provider = None
    if compose_provider and compose_form is None:
        compose_form = ServiceProviderMessageForm(
            initial={"provider_key": compose_provider["key"]}
        )

    return render(
        request,
        "farmers_dashboard/messages.html",
        _build_farmer_dashboard_context(
            request,
            page_title="Farmer Messages | CowCalving",
            page_eyebrow="Farmer messages",
            page_heading="Messages",
            page_intro="Open one conversation at a time, review cow context, and send a clear next update.",
            page_header_context="Messages and replies with the service team",
            header_primary_action={
                "label": "Find provider",
                "url": reverse("farmers_dashboard:service_finder"),
            },
            extra_context={
                "conversation_threads": thread_list,
                "selected_thread": selected_thread,
                "selected_thread_participants": _build_thread_participants_for_farmer(selected_thread)
                if selected_thread
                else None,
                "reply_form": reply_form,
                "compose_provider": compose_provider,
                "compose_form": compose_form,
            },
        ),
    )


@login_required
@role_required("farmer")
def notifications_view(request):
    notifications = list(get_notifications_for_user(request.user))
    if request.method == "POST":
        notification = get_object_or_404(
            get_notifications_for_user(request.user),
            pk=request.POST.get("notification_id"),
        )
        mark_notification_read(notification, request.user)
        if notification.action_url:
            return redirect(notification.action_url)
        return redirect("farmers_dashboard:notifications")

    return render(
        request,
        "farmers_dashboard/notifications.html",
        _build_farmer_dashboard_context(
            request,
            page_title="Farmer Notifications | CowCalving",
            page_eyebrow="Farmer alerts",
            page_heading="Notifications",
            page_intro="See what changed recently and jump straight to the next step.",
            page_header_context="Unread replies and workflow updates",
            header_primary_action={
                "label": "Open messages",
                "url": reverse("farmers_dashboard:messages"),
            },
            extra_context={
                "notifications": notifications,
                "notification_summary": {
                    "total": len(notifications),
                    "unread": sum(1 for item in notifications if not item.is_read),
                    "message_updates": sum(
                        1
                        for item in notifications
                        if item.notification_type == item.TYPE_PROVIDER_REPLIED
                    ),
                },
            },
        ),
    )


@login_required
@role_required("farmer")
def location_view(request):
    profile = get_profile(request.user)
    if request.method == "POST":
        form = FarmLocationForm(request.POST)
        if form.is_valid():
            profile.farm_latitude = form.cleaned_data["latitude"]
            profile.farm_longitude = form.cleaned_data["longitude"]
            profile.farm_location_source = form.cleaned_data["source"]
            profile.farm_location_updated_at = timezone.now()
            profile.save(
                update_fields=[
                    "farm_latitude",
                    "farm_longitude",
                    "farm_location_source",
                    "farm_location_updated_at",
                ]
            )
            messages.success(
                request,
                "Farm location saved. The veterinary dashboard can now use it for routing.",
            )
            return redirect("farmers_dashboard:location")
    else:
        form = FarmLocationForm(
            initial={
                "latitude": profile.farm_latitude,
                "longitude": profile.farm_longitude,
                "source": profile.farm_location_source or "manual_pin",
            }
        )

    location_state = _build_location_initial_state(profile)
    return render(
        request,
        "farmers_dashboard/location.html",
        _build_farmer_dashboard_context(
            request,
            page_title="Farm Location | CowCalving",
            page_eyebrow="Farm location",
            page_heading="Set farm location",
            page_intro="Pin your farm once so veterinary users can find the right destination quickly when follow-up is needed.",
            page_header_context="Save one clear farm pin for routing",
            header_primary_action={
                "label": "Open service finder",
                "url": reverse("farmers_dashboard:service_finder"),
            },
            extra_context={
                "location_form": form,
                "location_saved": profile.has_farm_location,
                "location_source_label": profile.farm_location_label,
                "location_updated_at": profile.farm_location_updated_at,
                "location_initial_state": location_state,
            },
        ),
    )


@login_required
@role_required("farmer")
def cow_register_view(request):
    if request.method == "POST":
        form = CowRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            cow = form.save(commit=False)
            cow.owner = request.user
            # Keep the tracker defaults and guided registration state aligned so
            # the user lands on the correct cow workflow page immediately after save.
            _apply_default_tracking_stage(cow)
            cow.save()
            if cow.reproductive_status == Cow.REPRODUCTIVE_STATUS_NOT_INSEMINATED:
                _ensure_open_insemination_request(cow)
            messages.success(request, f"{cow.name} was added to your herd.")
            return redirect("farmers_dashboard:cow_tracking", cow_id=cow.pk)
    else:
        form = CowRegistrationForm()

    return render(
        request,
        "farmers_dashboard/cow_register.html",
        _build_farmer_dashboard_context(
            request,
            page_title="Register Cow | CowCalving",
            page_eyebrow="New cow",
            page_heading="New Cow Registration",
            page_intro="Add the cow details, choose the reproductive starting point, and continue into the right tracker flow.",
            header_primary_action={
                "label": "Back to dashboard",
                "url": reverse("farmers_dashboard:dashboard"),
            },
            extra_context={"form": form},
        ),
    )


def _build_milk_trend(cow):
    recent_records = list(cow.milk_records.order_by("-record_date")[:14])
    if not recent_records:
        return {"records": [], "paths": [], "points": [], "summary": None}

    latest = recent_records[0]
    chronological = list(reversed(recent_records))
    previous_yields = [item.daily_yield_liters for item in chronological[:-1]][-7:]
    result = evaluate_milk_drop(latest, previous_yields)
    if result["level"] == "insufficient_history":
        missing_count = max(0, 7 - len(previous_yields))
        summary = {
            "tone": "neutral",
            "text": (
                f"Record {missing_count} more day{'s' if missing_count != 1 else ''} "
                "to compare with her previous 7 recorded days."
            ),
        }
    elif result["level"] == "unavailable":
        summary = {
            "tone": "neutral",
            "text": (
                f"Latest {latest.daily_yield_liters:.1f} L · previous 7 recorded days "
                "average 0 L, so a percentage comparison is unavailable."
            ),
        }
    elif result["level"] in {
        MilkProductionAlert.SEVERITY_WARNING,
        MilkProductionAlert.SEVERITY_CRITICAL,
    }:
        summary = {
            "tone": result["level"],
            "text": (
                f"Latest {latest.daily_yield_liters:.1f} L · usual "
                f"{result['baseline_yield_liters']:.1f} L · down "
                f"{result['drop_percent']:.0f}% ({result['level'].title()})."
            ),
        }
    elif result["level"] == "normal" and result["drop_percent"] > 0:
        summary = {
            "tone": "normal",
            "text": (
                f"Latest {latest.daily_yield_liters:.1f} L · usual "
                f"{result['baseline_yield_liters']:.1f} L · down "
                f"{result['drop_percent']:.0f}% (within the normal range)."
            ),
        }
    elif result["level"] == "normal" and result["drop_percent"] < 0:
        summary = {
            "tone": "normal",
            "text": (
                f"Latest {latest.daily_yield_liters:.1f} L · usual "
                f"{result['baseline_yield_liters']:.1f} L · up "
                f"{abs(result['drop_percent']):.0f}%."
            ),
        }
    else:
        summary = {
            "tone": "normal",
            "text": (
                f"Latest {latest.daily_yield_liters:.1f} L · usual "
                f"{result['baseline_yield_liters']:.1f} L · no change."
            ),
        }

    first_date = chronological[0].record_date
    last_date = latest.record_date
    date_span = (last_date - first_date).days
    span_days = max(1, date_span)
    plot_left = 58
    plot_right = 542
    plot_top = 14
    plot_bottom = 158
    max_yield = max(item.daily_yield_liters for item in chronological)
    raw_step = max(float(max_yield), 1) / 4
    step_power = 10 ** math.floor(math.log10(raw_step))
    normalized_step = raw_step / step_power
    if normalized_step <= 1:
        nice_step = 1
    elif normalized_step <= 2:
        nice_step = 2
    elif normalized_step <= 5:
        nice_step = 5
    else:
        nice_step = 10
    tick_step = nice_step * step_power
    axis_max = math.ceil(max(float(max_yield), tick_step) / tick_step) * tick_step
    tick_count = int(round(axis_max / tick_step))
    y_ticks = []
    for index in range(tick_count + 1):
        value = round(tick_step * index, 2)
        y = plot_bottom - (value / axis_max) * (plot_bottom - plot_top)
        y_ticks.append(
            {
                "label": f"{value:g}",
                "y": round(y, 1),
            }
        )

    date_tick_count = min(5, date_span + 1)
    x_ticks = []
    for index in range(date_tick_count):
        offset = (
            round(date_span * index / (date_tick_count - 1))
            if date_tick_count > 1
            else 0
        )
        tick_x = plot_left + (offset / span_days) * (
            plot_right - plot_left
        )
        if index == 0:
            anchor = "start"
        elif index == date_tick_count - 1:
            anchor = "end"
        else:
            anchor = "middle"
        x_ticks.append(
            {
                "date": first_date + timedelta(days=offset),
                "x": round(tick_x, 1),
                "anchor": anchor,
            }
        )

    plotted = []
    segments = []
    segment = []
    previous_date = None
    for item in chronological:
        x = plot_left + (
            (item.record_date - first_date).days / span_days
        ) * (plot_right - plot_left)
        y = plot_bottom - (float(item.daily_yield_liters) / axis_max) * (plot_bottom - plot_top)
        point = {
            "x": round(x, 1),
            "y": round(y, 1),
            "date": item.record_date,
            "yield": item.daily_yield_liters,
            "is_latest": item.pk == latest.pk,
        }
        if previous_date and (item.record_date - previous_date).days > 1:
            if len(segment) > 1:
                segments.append(" ".join(segment))
            segment = []
        command = f"{'M' if not segment else 'L'} {point['x']} {point['y']}"
        segment.append(command)
        plotted.append(point)
        previous_date = item.record_date
    if len(segment) > 1:
        segments.append(" ".join(segment))

    baseline_line = None
    if len(previous_yields) >= 7 and result.get("baseline_yield_liters"):
        baseline_start_date = chronological[-8].record_date
        baseline_start_x = plot_left + (
            (baseline_start_date - first_date).days / span_days
        ) * (plot_right - plot_left)
        baseline_y = plot_bottom - (
            float(result["baseline_yield_liters"]) / axis_max
        ) * (plot_bottom - plot_top)
        baseline_line = {
            "x1": round(baseline_start_x, 1),
            "x2": plot_right,
            "y": round(baseline_y, 1),
            "value": result["baseline_yield_liters"],
        }

    return {
        "records": chronological,
        "paths": segments,
        "points": plotted,
        "summary": summary,
        "start_date": first_date,
        "end_date": last_date,
        "x_ticks": x_ticks,
        "y_ticks": y_ticks,
        "plot_left": plot_left,
        "plot_right": plot_right,
        "plot_bottom": plot_bottom,
        "baseline_line": baseline_line,
    }


@login_required
@role_required("farmer")
def cow_tracking_view(request, cow_id):
    cow = get_object_or_404(
        Cow.objects.prefetch_related(
            Prefetch(
                "insemination_requests",
                queryset=InseminationRequest.objects.order_by("-submitted_at"),
            ),
            Prefetch(
                "reproductive_events",
                queryset=ReproductiveEvent.objects.select_related("recorded_by"),
            ),
        ),
        owner=request.user,
        pk=cow_id,
    )
    event_form = ReproductiveEventForm(
        cow=cow,
        initial={"event_date": timezone.localdate()},
    )
    attention_form = AttentionReasonForm()

    if request.method == "POST":
        next_stage = request.POST.get("tracking_stage", "").strip()
        toggle_attention = request.POST.get("toggle_attention")
        request_insemination = request.POST.get("request_insemination")
        record_event = request.POST.get("record_event")

        if next_stage and next_stage in dict(Cow.TRACKING_STAGE_CHOICES):
            cow.tracking_stage = next_stage
            _sync_tracking_stage(cow)
            if cow.tracking_stage == Cow.STAGE_POST_CALVING:
                cow.needs_attention = False
                cow.attention_reason = ""
            cow.save(
                update_fields=[
                    "tracking_stage",
                    "is_pregnant",
                    "needs_attention",
                    "attention_reason",
                    "updated_at",
                ]
            )
            messages.success(request, f"{cow.name} tracking stage updated.")
            return redirect(_build_tracking_redirect(cow.pk))

        if toggle_attention:
            if cow.needs_attention:
                cow.needs_attention = False
                cow.attention_reason = ""
                cow.save(
                    update_fields=["needs_attention", "attention_reason", "updated_at"]
                )
                messages.success(request, f"{cow.name} is now marked as stable.")
                return redirect(_build_tracking_redirect(cow.pk))

            attention_form = AttentionReasonForm(request.POST)
            if attention_form.is_valid():
                cow.needs_attention = True
                cow.attention_reason = attention_form.cleaned_data["attention_reason"]
                cow.save(
                    update_fields=["needs_attention", "attention_reason", "updated_at"]
                )
                messages.success(request, f"{cow.name} is now marked for a check.")
                return redirect(_build_tracking_redirect(cow.pk))

        if request_insemination:
            request_record = _ensure_open_insemination_request(cow)
            if request_record:
                messages.success(
                    request,
                    f"Insemination support has been requested for {cow.name}.",
                )
            else:
                messages.info(
                    request,
                    "This cow is no longer in the request stage.",
                )
            return redirect(_build_tracking_redirect(cow.pk))

        if record_event:
            event_form = ReproductiveEventForm(request.POST, cow=cow)
            if event_form.is_valid():
                with transaction.atomic():
                    event = _save_reproductive_event(
                        cow,
                        recorded_by=request.user,
                        event_type=event_form.cleaned_data["event_type"],
                        event_date=event_form.cleaned_data["event_date"],
                        notes=event_form.cleaned_data["notes"],
                    )
                messages.success(
                    request,
                    f"{event.get_event_type_display()} saved for {cow.name}.",
                )
                return redirect(_build_tracking_redirect(cow.pk))

    stage_options = _build_stage_options(cow)
    tracking_overview = _build_tracking_overview(cow)
    milk_trend = _build_milk_trend(cow)
    recent_milk_records = cow.milk_records.order_by("-record_date")[:5]

    return render(
        request,
        "farmers_dashboard/cow_tracking.html",
        _build_farmer_dashboard_context(
            request,
            page_title=f"{cow.name} Tracking | CowCalving",
            page_eyebrow="Cow tracking",
            page_heading="Cow tracker",
            page_header_title="Cow tracker",
            page_intro="Review the current reproductive path, then move through the calving stages and next actions for this cow.",
            header_primary_action={
                "label": "Back to herd",
                "url": reverse("farmers_dashboard:herd"),
            },
            extra_context={
                "cow": cow,
                "stage_options": stage_options,
                "active_insemination_request": cow.active_insemination_request,
                "tracking_overview": tracking_overview,
                "recent_milk_records": recent_milk_records,
                "milk_trend": milk_trend,
                "record_milk_url": f"{reverse('farmers_dashboard:milk_records')}?cow={cow.pk}",
                "event_form": event_form,
                "attention_form": attention_form,
                "tracking_form_action": _build_tracking_redirect(cow.pk),
            },
        ),
    )
