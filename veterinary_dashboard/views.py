import calendar
from statistics import fmean
from collections import defaultdict
from django.http import Http404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from communications.forms import ConversationReplyForm
from communications.services import (
    get_notifications_for_user,
    get_thread_for_user,
    get_threads_for_user,
    get_unread_notification_count,
    get_unread_thread_count,
    mark_notification_read,
    mark_thread_messages_read,
    send_thread_message,
)
from farmers_dashboard.models import Cow
from communications.models import ConversationMessage
from users.models import Profile
from users.permissions import role_required
from users.services import get_dashboard_url_for_user, get_or_create_profile


KENYA_MAP_CENTER = {"lat": -0.023559, "lng": 37.906193}


def _build_navigation_sections(unread_message_count=0, unread_notification_count=0):
    urgent_case_count = sum(
        1 for item in _build_patient_records() if item["tone"] == "rose"
    )
    return [
        {
            "label": "Main",
            "items": [
                {
                    "label": "Overview",
                    "url": reverse("veterinary_dashboard:dashboard"),
                    "view_name": "veterinary_dashboard:dashboard",
                    "icon": "overview",
                },
                {
                    "label": "Active Case",
                    "url": reverse("veterinary_dashboard:patients"),
                    "view_name": "veterinary_dashboard:patients",
                    "icon": "case",
                    "badge": str(urgent_case_count),
                },
                {
                    "label": "Farm Map",
                    "url": reverse("veterinary_dashboard:farm_map"),
                    "view_name": "veterinary_dashboard:farm_map",
                    "icon": "map",
                },
                {
                    "label": "Messages",
                    "url": reverse("veterinary_dashboard:messages"),
                    "view_name": "veterinary_dashboard:messages",
                    "icon": "messages",
                    "badge": str(unread_message_count) if unread_message_count else None,
                },
                {
                    "label": "Notifications",
                    "url": reverse("veterinary_dashboard:notifications"),
                    "view_name": "veterinary_dashboard:notifications",
                    "icon": "notifications",
                    "badge": str(unread_notification_count)
                    if unread_notification_count
                    else None,
                },
            ],
        },
        {
            "label": "Farms",
            "items": [
                {
                    "label": "My Farms",
                    "url": reverse("veterinary_dashboard:farms"),
                    "view_name": "veterinary_dashboard:farms",
                    "icon": "farms",
                    "badge": str(len(_build_farm_overview())),
                },
                {
                    "label": "Medical Records",
                    "url": reverse("veterinary_dashboard:medical_records"),
                    "view_name": "veterinary_dashboard:medical_records",
                    "icon": "records",
                },
            ],
        },
    ]


def _build_workspace_menu():
    return [
        {
            "label": "Account",
            "items": [
                {"label": "Overview", "description": "Return to the main command center.", "url": reverse("veterinary_dashboard:dashboard")},
                {"label": "My Profile", "description": "Review saved account details.", "url": reverse("users:profile")},
                {"label": "Edit Profile", "description": "Update account information.", "url": reverse("users:profile_edit")},
            ],
        },
        {
            "label": "Workspace",
            "items": [
                {"label": "Schedule", "description": "Open today's route planner.", "url": reverse("veterinary_dashboard:schedule")},
                {"label": "AI Workspace", "description": "Open guided support.", "url": reverse("cow_calving_ai:index")},
            ],
        },
    ]


def _build_summary_cards():
    overview_cases = _build_overview_case_rows()
    schedule_rows = _build_overview_schedule_rows()
    return [
        {
            "label": "Active cases",
            "value": str(len(overview_cases)),
            "detail": "Open patient files",
            "tone": "rose",
        },
        {
            "label": "Today's visits",
            "value": str(len(schedule_rows)),
            "detail": "Scheduled for today",
            "tone": "navy",
        },
        {
            "label": "Urgent now",
            "value": str(sum(1 for item in overview_cases if item["tone"] == "rose")),
            "detail": "Need immediate review",
            "tone": "amber",
        },
    ]


def _build_visit_cards():
    return [
        {"time": "08:00", "title": "Moi Farm - John Otieno", "detail": "Rosa #011 - labour complications - Kisii", "status": "Urgent", "tag": "Calving", "tone": "rose"},
        {"time": "10:30", "title": "Green Acres - Mary Wanjiku", "detail": "Herd vaccination - FMD booster - 8 cows", "status": "Scheduled", "tag": "Vaccination", "tone": "teal"},
        {"time": "14:00", "title": "Sunrise Dairy - Peter Kamau", "detail": "Daisy #003 - suspected mastitis - milk drop 30%", "status": "Pending", "tag": "Health check", "tone": "amber"},
    ]


def _build_priority_actions():
    return [
        {"title": "Urgent case", "detail": "Rosa #011 needs labour follow-up before 09:00.", "meta": "Telehealth ready", "tone": "rose"},
        {"title": "Lab review queue", "detail": "CBC and mastitis panels are ready for sign-off.", "meta": "3 pending", "tone": "navy"},
        {"title": "Prescription renewal", "detail": "Bella #004 requires treatment review today.", "meta": "Withholding note", "tone": "teal"},
    ]


def _build_farm_overview():
    return [
        {
            "name": "Moi Farm",
            "owner": "John Otieno",
            "location": "Kisii",
            "cow_count": 24,
            "alert_summary": "2 active alerts",
            "next_step": "Visit Rosa #011 first and confirm delivery progress.",
            "detail": "24 cows - 2 active alerts - Kisii",
            "risk": "High risk",
            "risk_percent": 86,
            "tone": "rose",
        },
        {
            "name": "Sunrise Dairy",
            "owner": "Peter Kamau",
            "location": "Kericho",
            "cow_count": 31,
            "alert_summary": "Mastitis review pending",
            "next_step": "Review Daisy #003 during the scheduled health check.",
            "detail": "31 cows - mastitis review pending - Kericho",
            "risk": "Medium risk",
            "risk_percent": 58,
            "tone": "amber",
        },
        {
            "name": "Green Acres",
            "owner": "Mary Wanjiku",
            "location": "Nakuru",
            "cow_count": 18,
            "alert_summary": "Vaccination plan on track",
            "next_step": "Keep the herd vaccination route on time.",
            "detail": "18 cows - vaccination plan on track - Nakuru",
            "risk": "Low risk",
            "risk_percent": 18,
            "tone": "teal",
        },
    ]


def _build_analytics_bars():
    return [
        {"label": "Mastitis", "value": "4 cases", "width": "80%", "tone": "rose"},
        {"label": "Difficult calving", "value": "2 cases", "width": "46%", "tone": "amber"},
        {"label": "Tick-borne fever", "value": "1 case", "width": "24%", "tone": "navy"},
    ]


def _build_lab_panels():
    return [
        {"title": "Complete blood count", "detail": "Nuru #025 - elevated WBC and low haematocrit need review.", "status": "Review first"},
        {"title": "Milk quality panel", "detail": "Rear-left quarter CMT is positive and SCC is above threshold.", "status": "Share after sign-off"},
    ]


def _build_case_snapshots():
    return [
        {"title": "Rosa #011", "detail": "Active labour case with escalation already in telehealth.", "status": "Open case", "tone": "rose"},
        {"title": "Bella #004", "detail": "Treatment course ends today and needs prescription review.", "status": "Rx follow-up", "tone": "amber"},
        {"title": "Nuru #025", "detail": "Lab interpretation is pending before farmer sharing.", "status": "Awaiting sign-off", "tone": "navy"},
    ]


def _build_patient_records():
    records = [
        {
            "id": "rosa-011",
            "name": "Rosa #011",
            "farm": "Moi Farm",
            "owner": "John Otieno",
            "location": "Kisii",
            "breed": "Ayrshire",
            "tag_number": "011",
            "status": "Open case",
            "tone": "rose",
            "issue": "Labour follow-up",
            "summary": "Active labour case with escalation already in telehealth.",
            "status_banner": "Labour in progress",
            "next_step": "Visit first and record delivery outcome.",
            "last_update": "08:04 today",
            "care_stages": ["Pre-calving", "Early labour", "Active labour", "Delivery", "Post-calving"],
            "current_stage": 2,
            "medical_note": "Cow presented BCS 2.8 at the last check. Monitor for dystocia risk and move quickly if contractions stall.",
            "medications": ["Oxytocin 10 IU", "Calcium borogluconate", "Lubricant gel", "Dystocia kit"],
            "ai_recommendation": "AI recommends maintaining close labour monitoring and escalating to assisted delivery if progress stalls after the next check-in.",
            "stats": [
                {"label": "Age", "value": "5 yr"},
                {"label": "Weight", "value": "390 kg"},
                {"label": "Parity", "value": "P3"},
                {"label": "Temp", "value": "39.2 C"},
            ],
            "history": [
                {"date": "09:12", "title": "Labour signs reported by farmer", "detail": "James Mwangi submitted an alert from the farm app."},
                {"date": "09:18", "title": "Vet acknowledged and reviewed remotely", "detail": "Remote assessment started after the escalation came through telehealth."},
                {"date": "09:45", "title": "Video call confirmed contractions", "detail": "Contractions reported every 8 minutes and farmer advised to prepare the pen."},
                {"date": "10:20", "title": "On-site follow-up arranged", "detail": "Field visit is underway with the labour kit ready."},
            ],
            "primary_url": reverse("veterinary_dashboard:diagnosis"),
            "primary_label": "Log update",
            "secondary_url": reverse("veterinary_dashboard:telehealth"),
            "secondary_label": "Call farmer",
            "extra_url": reverse("veterinary_dashboard:schedule"),
            "extra_label": "Open route",
            "stage_group": "assessment",
            "stage_group_label": "Assessment",
            "priority_group": "urgent",
            "priority_label": "Urgent",
        },
        {
            "id": "bella-004",
            "name": "Bella #004",
            "farm": "Moi Farm",
            "owner": "John Otieno",
            "location": "Kisii",
            "breed": "Friesian",
            "tag_number": "004",
            "status": "Rx follow-up",
            "tone": "amber",
            "issue": "Treatment renewal",
            "summary": "Treatment course ends today and needs prescription review.",
            "status_banner": "Treatment review due",
            "next_step": "Review medication and renew only if symptoms persist.",
            "last_update": "09:10 today",
            "care_stages": ["Reported", "Assessment", "Treatment", "Follow-up", "Closed"],
            "current_stage": 3,
            "medical_note": "Treatment is ending today. Review hydration, appetite, and udder status before renewing the prescription.",
            "medications": ["Oxytetracycline", "NSAID", "Milk withholding card"],
            "ai_recommendation": "AI recommends confirming symptom persistence before issuing a renewal and documenting withholding guidance for the farmer.",
            "stats": [
                {"label": "Age", "value": "4 yr"},
                {"label": "Weight", "value": "420 kg"},
                {"label": "Milk", "value": "16 L"},
                {"label": "Course", "value": "Ends today"},
            ],
            "history": [
                {"date": "18 Mar", "title": "Course review due", "detail": "Farmer reminded that current treatment finishes today."},
                {"date": "12 Mar", "title": "Initial diagnosis", "detail": "Clinical note recorded with antibiotic treatment plan."},
                {"date": "07 Jan", "title": "Routine check", "detail": "No active concerns recorded during herd review."},
            ],
            "primary_url": reverse("veterinary_dashboard:prescriptions"),
            "primary_label": "Open Rx",
            "secondary_url": reverse("veterinary_dashboard:diagnosis"),
            "secondary_label": "Open diagnosis",
            "extra_url": reverse("veterinary_dashboard:telehealth"),
            "extra_label": "Message farmer",
            "stage_group": "treatment",
            "stage_group_label": "Treatment",
            "priority_group": "needs_review",
            "priority_label": "Needs review",
        },
        {
            "id": "nuru-025",
            "name": "Nuru #025",
            "farm": "Moi Farm",
            "owner": "John Otieno",
            "location": "Kisii",
            "breed": "Jersey cross",
            "tag_number": "025",
            "status": "Awaiting sign-off",
            "tone": "navy",
            "issue": "Lab interpretation",
            "summary": "Lab interpretation is pending before farmer sharing.",
            "status_banner": "Lab review pending",
            "next_step": "Review CBC and milk panel before sending advice.",
            "last_update": "11:00 today",
            "care_stages": ["Sample sent", "Lab ready", "Review", "Share guidance", "Closed"],
            "current_stage": 2,
            "medical_note": "Elevated WBC and high SCC need veterinary interpretation before the farmer acts on the result.",
            "medications": ["CMT strips", "CBC panel", "Milk panel summary"],
            "ai_recommendation": "AI recommends linking the lab result to the active case note before issuing treatment guidance.",
            "stats": [
                {"label": "Age", "value": "3 yr"},
                {"label": "Weight", "value": "350 kg"},
                {"label": "WBC", "value": "14.8"},
                {"label": "SCC", "value": "450k"},
            ],
            "history": [
                {"date": "20 Mar", "title": "CBC ready", "detail": "Elevated WBC and low haematocrit flagged for veterinary review."},
                {"date": "19 Mar", "title": "Milk panel", "detail": "Rear-left quarter CMT positive with high SCC."},
                {"date": "02 Feb", "title": "Routine milk check", "detail": "Previous milk quality panel returned within range."},
            ],
            "primary_url": reverse("veterinary_dashboard:labs"),
            "primary_label": "Open labs",
            "secondary_url": reverse("veterinary_dashboard:diagnosis"),
            "secondary_label": "Add findings",
            "extra_url": reverse("veterinary_dashboard:telehealth"),
            "extra_label": "Share later",
            "stage_group": "waiting_result",
            "stage_group_label": "Waiting on result",
            "priority_group": "needs_review",
            "priority_label": "Needs review",
        },
        {
            "id": "daisy-003",
            "name": "Daisy #003",
            "farm": "Sunrise Dairy",
            "owner": "Peter Kamau",
            "location": "Kericho",
            "breed": "Friesian",
            "tag_number": "003",
            "status": "Pending visit",
            "tone": "amber",
            "issue": "Suspected mastitis",
            "summary": "Symptoms logged ahead of the afternoon visit with milk drop reported.",
            "status_banner": "Visit pending",
            "next_step": "Confirm mastitis signs during the 14:00 health check.",
            "last_update": "11:40 today",
            "care_stages": ["Reported", "Remote triage", "Visit scheduled", "Treatment", "Recovery"],
            "current_stage": 2,
            "medical_note": "Farmer reported milk drop and tenderness. Confirm quarter involvement and rule out fever on site.",
            "medications": ["CMT kit", "Thermometer", "Intramammary tube"],
            "ai_recommendation": "AI recommends confirming mastitis severity during the visit before choosing between local treatment and full escalation.",
            "stats": [
                {"label": "Age", "value": "6 yr"},
                {"label": "Weight", "value": "410 kg"},
                {"label": "Milk", "value": "-30%"},
                {"label": "Visit", "value": "14:00"},
            ],
            "history": [
                {"date": "20 Mar", "title": "Telehealth note", "detail": "Farmer logged mastitis symptoms before field visit."},
                {"date": "15 Jan", "title": "Herd review", "detail": "Routine check completed with no treatment required."},
                {"date": "04 Oct", "title": "Vaccination", "detail": "Scheduled herd vaccination completed."},
            ],
            "primary_url": reverse("veterinary_dashboard:schedule"),
            "primary_label": "Open schedule",
            "secondary_url": reverse("veterinary_dashboard:telehealth"),
            "secondary_label": "Open telehealth",
            "extra_url": reverse("veterinary_dashboard:labs"),
            "extra_label": "Review labs",
            "stage_group": "follow_up",
            "stage_group_label": "Follow-up",
            "priority_group": "needs_review",
            "priority_label": "Needs review",
        },
    ]

    for record in records:
        record["list_summary"] = record["next_step"]

    return records


def _build_prescription_notes():
    return [
        {"title": "Milk withholding warning", "detail": "Keep withholding guidance visible on every treatment summary before sending to the farmer.", "status": "Safety first", "tone": "amber"},
        {"title": "Dose validation", "detail": "Check weight-based dosing from the patient file before issuing or renewing Rx.", "status": "Clinical check", "tone": "navy"},
        {"title": "Renewal reminders", "detail": "Group ending courses into one follow-up list instead of scattering them across pages.", "status": "Workflow", "tone": "teal"},
    ]


def _build_telehealth_updates():
    return [
        {"farmer": "John Otieno", "message": "Labour case update received with photo evidence.", "time": "08:04"},
        {"farmer": "Mary Wanjiku", "message": "Vaccination visit confirmed for the 10:30 slot.", "time": "09:12"},
        {"farmer": "Peter Kamau", "message": "Mastitis symptoms logged ahead of the afternoon visit.", "time": "11:40"},
    ]


def _build_schedule_planner():
    # Keep the hackathon schedule flow simple and demo-friendly: one visible
    # month, a selected day, and a small set of realistic visit records.
    year = 2026
    month = 3
    selected_day = 20

    visits_by_day = {
        20: [
            {
                "id": "moi-labour",
                "time": "08:00",
                "farm": "Moi Farm",
                "farmer": "John Otieno",
                "animal": "Rosa #011",
                "type": "Labour follow-up",
                "detail": "Labour complications - Kisii",
                "status": "Urgent",
                "tone": "rose",
                "primary_url": reverse("veterinary_dashboard:telehealth"),
                "primary_label": "Open telehealth",
                "secondary_url": reverse("veterinary_dashboard:patients"),
                "secondary_label": "Open case",
            },
            {
                "id": "green-acres-vax",
                "time": "10:30",
                "farm": "Green Acres",
                "farmer": "Mary Wanjiku",
                "animal": "Herd visit",
                "type": "Vaccination",
                "detail": "FMD booster - 8 cows",
                "status": "Scheduled",
                "tone": "emerald",
                "primary_url": reverse("veterinary_dashboard:patients"),
                "primary_label": "Open patients",
                "secondary_url": reverse("veterinary_dashboard:diagnosis"),
                "secondary_label": "Add note",
            },
            {
                "id": "sunrise-mastitis",
                "time": "14:00",
                "farm": "Sunrise Dairy",
                "farmer": "Peter Kamau",
                "animal": "Daisy #003",
                "type": "Health check",
                "detail": "Suspected mastitis - milk drop 30%",
                "status": "Pending",
                "tone": "amber",
                "primary_url": reverse("veterinary_dashboard:patients"),
                "primary_label": "Open patient",
                "secondary_url": reverse("veterinary_dashboard:labs"),
                "secondary_label": "Open labs",
            },
        ],
        21: [
            {
                "id": "baraka-route",
                "time": "09:15",
                "farm": "Baraka Ranch",
                "farmer": "Samuel Kipchoge",
                "animal": "Herd visit",
                "type": "Routine check",
                "detail": "Quarterly herd health check",
                "status": "Scheduled",
                "tone": "emerald",
                "primary_url": reverse("veterinary_dashboard:farms"),
                "primary_label": "Open farm",
                "secondary_url": reverse("veterinary_dashboard:patients"),
                "secondary_label": "Open files",
            }
        ],
        24: [
            {
                "id": "nuru-lab-review",
                "time": "11:00",
                "farm": "Moi Farm",
                "farmer": "John Otieno",
                "animal": "Nuru #025",
                "type": "Lab review",
                "detail": "CBC and mastitis panel sign-off",
                "status": "Review",
                "tone": "navy",
                "primary_url": reverse("veterinary_dashboard:labs"),
                "primary_label": "Review labs",
                "secondary_url": reverse("veterinary_dashboard:patients"),
                "secondary_label": "Open patient",
            }
        ],
        26: [
            {
                "id": "ngugi-follow-up",
                "time": "15:30",
                "farm": "Ngugi Family Farm",
                "farmer": "Grace Ngugi",
                "animal": "Vaccination drive",
                "type": "Follow-up",
                "detail": "3 cows overdue for vaccination",
                "status": "Pending",
                "tone": "amber",
                "primary_url": reverse("veterinary_dashboard:farms"),
                "primary_label": "Open farms",
                "secondary_url": reverse("veterinary_dashboard:telehealth"),
                "secondary_label": "Message farmer",
            }
        ],
    }

    month_weeks = calendar.Calendar(firstweekday=0).monthdayscalendar(year, month)
    calendar_days = []
    for week in month_weeks:
        for day in week:
            if day == 0:
                calendar_days.append({"empty": True})
                continue

            visits = visits_by_day.get(day, [])
            tones = {item["tone"] for item in visits}
            calendar_days.append(
                {
                    "day": day,
                    "empty": False,
                    "selected": day == selected_day,
                    "visit_count": len(visits),
                    "has_urgent": "rose" in tones,
                    "has_items": bool(visits),
                }
            )

    selected_visits = visits_by_day[selected_day]
    total_planned_days = len([day for day, items in visits_by_day.items() if items])
    total_urgent_visits = sum(
        1
        for items in visits_by_day.values()
        for item in items
        if item["tone"] == "rose"
    )
    return {
        "month_label": f"{calendar.month_name[month]} {year}",
        "weekday_labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "calendar_days": calendar_days,
        "selected_day": selected_day,
        "selected_date_label": "Friday, 20 March 2026",
        "selected_day_summary": "3 visits planned, 1 urgent case, 1 follow-up pending.",
        "schedule_seed_items": visits_by_day,
        "schedule_initial_items": selected_visits,
        "planner_stats": [
            {"label": "Planned days", "value": str(total_planned_days)},
            {"label": "Urgent visits", "value": str(total_urgent_visits)},
            {"label": "Assigned farms", "value": "4"},
        ],
        "planner_help": [
            "Pick a date on the calendar to review that day's route.",
            "Use Add visit to draft a new assignment in this browser for the demo.",
            "Open the linked patient, lab, or telehealth page only when needed.",
        ],
    }


def _build_dashboard_greeting() -> str:
    hour = timezone.localtime().hour
    if hour < 12:
        return "good morning"
    if hour < 18:
        return "good afternoon"
    return "good evening"


def _build_overview_case_rows():
    case_flags = {
        "rose": "Respond now",
        "amber": "Monitor",
        "navy": "Review",
    }
    rows = []
    for record in _build_patient_records():
        rows.append(
            {
                "code": f"#C-{record['tag_number']}",
                "detail": f"{record['farm']} · {record['issue']}",
                "flag": case_flags.get(record["tone"], record["status"]),
                "tone": record["tone"],
            }
        )
    return rows


def _build_dashboard_farm_cards():
    farm_flags = {
        "rose": "2 urgent",
        "amber": "Monitoring",
        "teal": "Stable",
    }
    cards = []
    for farm in _build_farm_overview():
        words = farm["name"].replace("-", " ").split()
        initials = "".join(word[0].upper() for word in words[:2] if word) or "FM"
        cards.append(
            {
                "name": farm["name"],
                "detail": farm["detail"],
                "flag": farm_flags.get(farm["tone"], farm["risk"]),
                "initials": initials,
                "tone": farm["tone"],
            }
        )
    return cards


def _build_overview_schedule_rows():
    return [
        {
            "time": "08:00",
            "farm": "Moi Farm",
            "visit_type": "Pre-calving check",
            "detail": "Cow #C-055",
        },
        {
            "time": "10:30",
            "farm": "Green Acres",
            "visit_type": "Vaccination run",
            "detail": "8 cows",
        },
        {
            "time": "14:00",
            "farm": "Moi Farm",
            "visit_type": "Follow-up check",
            "detail": "Calf #B-009",
        },
    ]


def _build_dashboard_quick_links():
    return [
        {
            "label": "Open farm map",
            "description": "Check the region visually when routing needs more context than the overview shows.",
            "url": reverse("veterinary_dashboard:farm_map"),
        },
        {
            "label": "My farms",
            "description": "Review assigned farms only when you need counts, alerts, and due-soon work.",
            "url": reverse("veterinary_dashboard:farms"),
        },
        {
            "label": "Medical records",
            "description": "Open treatment history and recent lab summaries without crowding the homepage.",
            "url": reverse("veterinary_dashboard:medical_records"),
        },
    ]


def _build_farm_marker_label(profile):
    farm_name = (profile.farm_name or "").strip()
    if farm_name:
        parts = [part[0].upper() for part in farm_name.split()[:2] if part]
        if parts:
            return "".join(parts)[:2]
    display_name = profile.user.get_full_name().strip() or profile.user.username
    parts = [part[0].upper() for part in display_name.split()[:2] if part]
    return ("".join(parts) or "FM")[:2]


def _build_directions_url(profile):
    return (
        "https://www.google.com/maps/dir/?api=1&destination="
        f"{profile.farm_latitude},{profile.farm_longitude}"
    )


def _build_farm_map_context(veterinary_user):
    farmer_profiles = list(
        Profile.objects.filter(
            role__slug="farmer",
            farm_latitude__isnull=False,
            farm_longitude__isnull=False,
        )
        .select_related("user", "role")
        .order_by("farm_name", "user__username")
    )

    cows = list(
        Cow.objects.filter(owner__profile__in=farmer_profiles).select_related("owner")
    )
    cows_by_owner_id = {}
    for cow in cows:
        cows_by_owner_id.setdefault(cow.owner_id, []).append(cow)

    unread_messages_by_farmer_id = defaultdict(int)
    unread_farmer_messages = (
        ConversationMessage.objects.filter(
            read_at__isnull=True,
            sender__profile__role__slug="farmer",
            thread__farmer__profile__in=farmer_profiles,
        )
        .filter(
            Q(thread__assigned_veterinary_user=veterinary_user)
            | Q(thread__assigned_veterinary_user__isnull=True)
        )
        .values_list("thread__farmer_id", flat=True)
    )
    for farmer_id in unread_farmer_messages:
        unread_messages_by_farmer_id[farmer_id] += 1

    markers = []
    farm_cards = []
    urgent_count = 0
    due_soon_farm_count = 0
    unread_message_farm_count = 0
    for profile in farmer_profiles:
        owner_cows = cows_by_owner_id.get(profile.user_id, [])
        due_soon_count = sum(1 for cow in owner_cows if cow.is_nearing_calving())
        alert_count = sum(1 for cow in owner_cows if cow.needs_attention)
        unread_message_count = unread_messages_by_farmer_id.get(profile.user_id, 0)
        has_urgent = alert_count > 0
        has_due_soon = due_soon_count > 0
        has_unread_messages = unread_message_count > 0
        if alert_count:
            tone = "rose"
            badge = f"{alert_count} active"
        elif due_soon_count:
            tone = "amber"
            badge = f"{due_soon_count} due soon"
        else:
            tone = "teal"
            badge = "Location saved"

        urgent_count += int(has_urgent)
        due_soon_farm_count += int(has_due_soon)
        unread_message_farm_count += int(has_unread_messages)

        display_name = profile.user.get_full_name().strip() or profile.user.username
        farm_name = profile.farm_name or f"{display_name} Farm"
        markers.append(
            {
                "id": f"farm-{profile.pk}",
                "label": _build_farm_marker_label(profile),
                "name": farm_name,
                "owner": display_name,
                "phone": profile.phone_number,
                "status": badge,
                "tone": tone,
                "lat": float(profile.farm_latitude),
                "lng": float(profile.farm_longitude),
                "has_urgent": has_urgent,
                "has_due_soon": has_due_soon,
                "has_unread_messages": has_unread_messages,
                "unread_message_count": unread_message_count,
                "directions_url": _build_directions_url(profile),
            }
        )
        farm_cards.append(
            {
                "id": f"farm-{profile.pk}",
                "name": farm_name,
                "owner": display_name,
                "phone": profile.phone_number or "No phone saved",
                "cows": str(len(owner_cows)),
                "due_soon": str(due_soon_count),
                "alerts": f"{alert_count} active" if alert_count else "None",
                "badge": badge,
                "tone": tone,
                "has_urgent": has_urgent,
                "has_due_soon": has_due_soon,
                "has_unread_messages": has_unread_messages,
                "unread_message_count": unread_message_count,
                "directions_url": _build_directions_url(profile),
            }
        )

    if markers:
        center_lat = fmean(marker["lat"] for marker in markers)
        center_lng = fmean(marker["lng"] for marker in markers)
        zoom = 8 if len(markers) > 1 else 12
    else:
        center_lat = KENYA_MAP_CENTER["lat"]
        center_lng = KENYA_MAP_CENTER["lng"]
        zoom = 6

    return {
        "region_label": "Saved farm locations",
        "vet_status_label": (
            f"{len(markers)} farm pin{'s' if len(markers) != 1 else ''} ready for routing"
            if markers
            else "No saved farm locations yet"
        ),
        "legend_items": [
            {"label": "Needs attention", "tone": "rose"},
            {"label": "Due soon", "tone": "amber"},
            {"label": "Unread farmer message", "tone": "navy"},
            {"label": "Location saved", "tone": "teal"},
        ],
        "filter_options": [
            {"value": "all", "label": "All farms", "count": len(farm_cards)},
            {"value": "urgent", "label": "Urgent", "count": urgent_count},
            {"value": "due_soon", "label": "Due soon", "count": due_soon_farm_count},
            {
                "value": "unread_messages",
                "label": "Unread farmer messages",
                "count": unread_message_farm_count,
            },
        ],
        "map_center": {"lat": center_lat, "lng": center_lng, "zoom": zoom},
        "map_markers": markers,
        "status_cards": farm_cards,
    }


def _build_medical_record_cards():
    return [
        {
            "title": "Rosa #011",
            "farm": "Moi Farm",
            "owner": "John Otieno",
            "record_type": "Labour follow-up",
            "updated_at": "Today 10:20",
            "next_step": "Open the active case and record the delivery outcome.",
            "detail": "Labour follow-up timeline, intervention summary, and escalation notes.",
            "status": "Open case",
            "tone": "rose",
        },
        {
            "title": "Bella #004",
            "farm": "Moi Farm",
            "owner": "John Otieno",
            "record_type": "Treatment renewal",
            "updated_at": "18 Mar",
            "next_step": "Confirm symptoms before renewing the prescription.",
            "detail": "Treatment renewal review with withholding guidance recorded.",
            "status": "Follow-up",
            "tone": "amber",
        },
        {
            "title": "Nuru #025",
            "farm": "Moi Farm",
            "owner": "John Otieno",
            "record_type": "Lab review",
            "updated_at": "20 Mar",
            "next_step": "Sign off the CBC and milk panel before sharing guidance.",
            "detail": "CBC and milk panel results waiting for sign-off and farmer sharing.",
            "status": "Lab linked",
            "tone": "navy",
        },
    ]


def _build_common_context(request, *, page_title, page_eyebrow, page_heading, page_intro):
    profile = get_or_create_profile(request.user)
    display_name = request.user.get_full_name().strip() or request.user.username
    initials = "".join(part[0].upper() for part in display_name.split()[:2] if part) or "VT"
    unread_message_count = get_unread_thread_count(request.user)
    unread_notification_count = get_unread_notification_count(request.user)
    return {
        "dashboard_home_url": get_dashboard_url_for_user(request.user, fallback="/dashboard/profile/"),
        "back_to_website_url": reverse("Core_Web:home"),
        "ai_workspace_url": reverse("cow_calving_ai:index"),
        "ai_workspace_embed_url": f"{reverse('cow_calving_ai:index')}?embedded=1",
        "profile": profile,
        "display_name": display_name,
        "vet_initials": initials,
        "professional_id_display": profile.professional_id or "KE-VET-4921",
        "dashboard_greeting": _build_dashboard_greeting(),
        "page_title": page_title,
        "page_eyebrow": page_eyebrow,
        "page_heading": page_heading,
        "page_intro": page_intro,
        "navigation_sections": _build_navigation_sections(
            unread_message_count,
            unread_notification_count,
        ),
        "workspace_menu_sections": _build_workspace_menu(),
        "unread_message_count": unread_message_count,
        "unread_notification_count": unread_notification_count,
        "header_primary_action": {
            "label": "New case update",
            "url": reverse("veterinary_dashboard:patients"),
        },
    }


def _build_workspace_page_context(request, *, page_title, page_eyebrow, page_heading, page_intro, page_focus, page_quick_actions, main_section, support_section, extra_section):
    context = _build_common_context(
        request,
        page_title=page_title,
        page_eyebrow=page_eyebrow,
        page_heading=page_heading,
        page_intro=page_intro,
    )
    context.update(
        {
            "page_focus": page_focus,
            "page_quick_actions": page_quick_actions,
            "main_section": main_section,
            "support_section": support_section,
            "extra_section": extra_section,
        }
    )
    return context


def _build_thread_participants_for_veterinary(thread):
    farmer_name = thread.farmer.get_full_name().strip() or thread.farmer.username
    farm_name = getattr(thread.farmer.profile, "farm_name", "") if hasattr(thread.farmer, "profile") else ""
    return {
        "title": farmer_name,
        "subtitle": farm_name or "Farmer account",
        "meta": thread.cow.name if thread.cow else "General support",
    }


def _load_veterinary_message_state(request, thread_id=None):
    selected_thread = None
    if thread_id is not None:
        selected_thread = get_thread_for_user(request.user, thread_id)
        if selected_thread is None:
            raise Http404("Conversation not found.")

    if selected_thread is None:
        thread_list = get_threads_for_user(request.user)
        if thread_list:
            selected_thread = thread_list[0]

    if selected_thread is not None:
        mark_thread_messages_read(selected_thread, request.user)

    thread_list = get_threads_for_user(request.user)
    if selected_thread is not None:
        selected_thread = next(
            (thread for thread in thread_list if thread.pk == selected_thread.pk),
            selected_thread,
        )
    return thread_list, selected_thread


@login_required
@role_required("veterinary")
def dashboard_view(request):
    context = _build_common_context(
        request,
        page_title="Veterinary Dashboard | CowCalving",
        page_eyebrow="Clinical operations",
        page_heading="Veterinary Dashboard",
        page_intro="Track urgent work, today's visits, and pending reviews.",
    )
    context.update(
        {
            "summary_cards": _build_summary_cards(),
            "overview_schedule_rows": _build_overview_schedule_rows(),
            # Keep the overview data intentionally compact so the dashboard
            # stays close to the shared mockup and leaves deeper workflows for
            # dedicated pages like patients, schedule, and farms.
            "overview_case_rows": _build_overview_case_rows(),
            "dashboard_quick_links": _build_dashboard_quick_links(),
        }
    )
    return render(request, "veterinary_dashboard/dashboard.html", context)


@login_required
@role_required("veterinary")
def messages_view(request, thread_id=None):
    selected_thread = None
    if thread_id is not None:
        selected_thread = get_thread_for_user(request.user, thread_id)
        if selected_thread is None:
            raise Http404("Conversation not found.")

    if request.method == "POST":
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
            messages.success(request, "Reply sent to the farmer.")
            return redirect("veterinary_dashboard:messages_thread", thread_id=selected_thread.pk)
    else:
        reply_form = ConversationReplyForm()

    thread_list, selected_thread = _load_veterinary_message_state(
        request,
        thread_id=thread_id,
    )

    context = _build_common_context(
        request,
        page_title="Veterinary Messages | CowCalving",
        page_eyebrow="Clinical messaging",
        page_heading="Messages",
        page_intro="Review farmer context, attachments, and the next reply in one focused inbox.",
    )
    context.update(
        {
            "header_primary_action": {
                "label": "Open notifications",
                "url": reverse("veterinary_dashboard:notifications"),
            },
            "conversation_threads": thread_list,
            "selected_thread": selected_thread,
            "selected_thread_participants": _build_thread_participants_for_veterinary(selected_thread)
            if selected_thread
            else None,
            "reply_form": reply_form,
        }
    )
    return render(request, "veterinary_dashboard/messages.html", context)


@login_required
@role_required("veterinary")
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
        return redirect("veterinary_dashboard:notifications")

    context = _build_common_context(
        request,
        page_title="Veterinary Notifications | CowCalving",
        page_eyebrow="Clinical alerts",
        page_heading="Notifications",
        page_intro="Prioritize new farmer messages and open the right case context quickly.",
    )
    context.update(
        {
            "header_primary_action": {
                "label": "Open inbox",
                "url": reverse("veterinary_dashboard:messages"),
            },
            "notifications": notifications,
            "notification_summary": {
                "total": len(notifications),
                "unread": sum(1 for item in notifications if not item.is_read),
                "new_farmer_messages": sum(
                    1
                    for item in notifications
                    if item.notification_type == item.TYPE_NEW_FARMER_MESSAGE
                ),
            },
        }
    )
    return render(request, "veterinary_dashboard/notifications.html", context)


@login_required
@role_required("veterinary")
def schedule_view(request):
    context = _build_common_context(
        request,
        page_title="Veterinary Schedule | CowCalving",
        page_eyebrow="Schedule",
        page_heading="Plan the day clearly",
        page_intro="Use one simple planner for visits, follow-up, and route order.",
    )
    context.update(_build_schedule_planner())
    return render(request, "veterinary_dashboard/schedule.html", context)


@login_required
@role_required("veterinary")
def farms_view(request):
    farms = _build_farm_overview()
    context = _build_common_context(
        request,
        page_title="Veterinary Farms | CowCalving",
        page_eyebrow="My farms",
        page_heading="Manage assigned farms",
        page_intro="Keep the farm list short, scannable, and easy to connect to routes, alerts, and follow-up.",
    )
    context.update(
        {
            "header_primary_action": {
                "label": "Open farm map",
                "url": reverse("veterinary_dashboard:farm_map"),
            },
            "farm_records": farms,
            "farm_summary": {
                "total": len(farms),
                "high_risk": sum(1 for farm in farms if farm["tone"] == "rose"),
                "needs_planning": sum(1 for farm in farms if farm["tone"] == "amber"),
            },
            "farm_support_actions": [
                {"label": "Open schedule", "description": "Compare farm risk with today's route order.", "url": reverse("veterinary_dashboard:schedule")},
                {"label": "Open active case", "description": "Move from the farm list into the next animal that needs action.", "url": reverse("veterinary_dashboard:patients")},
                {"label": "Open medical records", "description": "Review recent treatment and lab context for the farm.", "url": reverse("veterinary_dashboard:medical_records")},
            ],
        }
    )
    return render(request, "veterinary_dashboard/farms.html", context)


@login_required
@role_required("veterinary")
def patients_view(request):
    patient_records = _build_patient_records()
    context = _build_common_context(
        request,
        page_title="Veterinary Active Case | CowCalving",
        page_eyebrow="Active case",
        page_heading="Work from one active case at a time",
        page_intro="Keep the case queue short, open one animal, and make the next action obvious for the vet.",
    )
    context.update(
        {
            "patient_records": patient_records,
            "patient_stats": [
                {"label": "Open cases", "value": str(len(patient_records))},
                {
                    "label": "Urgent",
                    "value": str(
                        sum(
                            1
                            for item in patient_records
                            if item["priority_group"] == "urgent"
                        )
                    ),
                },
                {
                    "label": "Waiting result",
                    "value": str(
                        sum(
                            1
                            for item in patient_records
                            if item["stage_group"] == "waiting_result"
                        )
                    ),
                },
            ],
            "patient_page_notes": [
                "Open one case, act, then come back for the next one.",
                "Keep telehealth, diagnosis, and routing behind action buttons so the page stays controlled.",
                "Save a short local note first, then move to the next workflow only if needed.",
            ],
            "patient_seed_record": patient_records[0],
        }
    )
    return render(request, "veterinary_dashboard/patients.html", context)


@login_required
@role_required("veterinary")
def farm_map_view(request):
    context = _build_common_context(
        request,
        page_title="Veterinary Farm Map | CowCalving",
        page_eyebrow="Farm map",
        page_heading="Read the region at a glance",
        page_intro="Use the map only when the route or farm priority needs a wider view than the overview can show.",
    )
    context.update(_build_farm_map_context(request.user))
    return render(request, "veterinary_dashboard/farm_map.html", context)


@login_required
@role_required("veterinary")
def medical_records_view(request):
    records = _build_medical_record_cards()
    context = _build_common_context(
        request,
        page_title="Veterinary Medical Records | CowCalving",
        page_eyebrow="Medical records",
        page_heading="Review concise case history",
        page_intro="Keep treatment history, lab summaries, and recent case notes accessible without crowding live case work.",
    )
    context.update(
        {
            "header_primary_action": {
                "label": "Open active case",
                "url": reverse("veterinary_dashboard:patients"),
            },
            "record_items": records,
            "record_summary": {
                "total": len(records),
                "open_case": sum(1 for item in records if item["tone"] == "rose"),
                "awaiting_review": sum(1 for item in records if item["tone"] in {"amber", "navy"}),
            },
            "record_support_actions": [
                {"label": "Open labs", "description": "Review full lab detail when a summary is not enough.", "url": reverse("veterinary_dashboard:labs")},
                {"label": "Open prescriptions", "description": "Check treatment planning after reading the recent history.", "url": reverse("veterinary_dashboard:prescriptions")},
                {"label": "Open farm map", "description": "Switch to the region view if the next step becomes a visit.", "url": reverse("veterinary_dashboard:farm_map")},
            ],
        }
    )
    return render(request, "veterinary_dashboard/medical_records.html", context)


@login_required
@role_required("veterinary")
def diagnosis_view(request):
    return render(
        request,
        "veterinary_dashboard/workspace_page.html",
        _build_workspace_page_context(
            request,
            page_title="Veterinary Diagnosis | CowCalving",
            page_eyebrow="Diagnosis",
            page_heading="Record the assessment",
            page_intro="Keep findings and next steps together.",
            page_focus={"label": "Diagnosis", "title": "Keep assessment work focused", "text": "Use one page for findings, severity, and the next action.", "badges": ["Severity first", "Structured notes", "Clear handoff"]},
            page_quick_actions=[
                {"label": "Open patient files", "description": "Review the case first.", "url": reverse("veterinary_dashboard:patients")},
                {"label": "Open Rx workflow", "description": "Prepare treatment next.", "url": reverse("veterinary_dashboard:prescriptions")},
                {"label": "Open telehealth", "description": "Send a farmer update.", "url": reverse("veterinary_dashboard:telehealth")},
            ],
            main_section={"label": "Diagnosis queue", "title": "Cases needing clinical attention", "cards": _build_priority_actions()},
            support_section={"label": "Workflow notes", "title": "How to reduce diagnosis friction", "cards": [
                {"title": "Capture only what drives action", "detail": "Use findings, severity, and treatment direction first before opening secondary detail.", "status": "Shorter forms", "tone": "teal"},
                {"title": "Keep note flow linear", "detail": "Patient file, diagnosis, then prescription is easier to remember than mixing all three together.", "status": "Cleaner mental model", "tone": "navy"},
                {"title": "Separate lab interpretation", "detail": "Leave deep result review on the lab page so diagnosis screens stay concise.", "status": "Dedicated review", "tone": "amber"},
            ]},
            extra_section={"label": "After diagnosis", "title": "The next likely pages", "cards": [
                {"title": "Prescriptions", "detail": "Move from diagnosis into medication, route, and withholding guidance.", "url": reverse("veterinary_dashboard:prescriptions")},
                {"title": "Labs", "detail": "Review supporting diagnostics if more evidence is needed.", "url": reverse("veterinary_dashboard:labs")},
                {"title": "Dashboard", "detail": "Return to the lighter overview once active case work is done.", "url": reverse("veterinary_dashboard:dashboard")},
            ]},
        ),
    )


@login_required
@role_required("veterinary")
def prescriptions_view(request):
    return render(
        request,
        "veterinary_dashboard/workspace_page.html",
        _build_workspace_page_context(
            request,
            page_title="Veterinary Prescriptions | CowCalving",
            page_eyebrow="Prescription workflow",
            page_heading="Issue treatment safely",
            page_intro="Keep medication details in one dedicated page.",
            page_focus={"label": "Prescriptions", "title": "Keep treatment clear and safe", "text": "Use this page for medication, withholding, and follow-up.", "badges": ["Safety checks", "Dose clarity", "Follow-up"]},
            page_quick_actions=[
                {"label": "Open diagnosis", "description": "Return to the note.", "url": reverse("veterinary_dashboard:diagnosis")},
                {"label": "Open patients", "description": "Confirm case and weight.", "url": reverse("veterinary_dashboard:patients")},
                {"label": "Open telehealth", "description": "Send the care plan.", "url": reverse("veterinary_dashboard:telehealth")},
            ],
            main_section={"label": "Prescription notes", "title": "Safety checks that must stay visible", "cards": _build_prescription_notes()},
            support_section={"label": "Design rule", "title": "Why Rx deserves its own page", "cards": [
                {"title": "Do not bury withholding periods", "detail": "Farmer-facing risk notes need a consistent place where they cannot be missed.", "status": "Legal and practical", "tone": "amber"},
                {"title": "Keep medication separate from notes", "detail": "Assessment and treatment are connected, but they are easier to review on separate pages.", "status": "Cleaner review", "tone": "navy"},
                {"title": "Use one renewal list", "detail": "A dedicated prescription page is the right home for course endings and refill reminders.", "status": "Less duplication", "tone": "teal"},
            ]},
            extra_section={"label": "Connected pages", "title": "What feeds the prescription workflow", "cards": [
                {"title": "Patient files", "detail": "Open the patient context before issuing treatment.", "url": reverse("veterinary_dashboard:patients")},
                {"title": "Diagnosis", "detail": "Return to findings if the medication plan needs adjustment.", "url": reverse("veterinary_dashboard:diagnosis")},
                {"title": "Telehealth", "detail": "Share final instructions after the prescription is ready.", "url": reverse("veterinary_dashboard:telehealth")},
            ]},
        ),
    )


@login_required
@role_required("veterinary")
def labs_view(request):
    lab_cards = [{"title": panel["title"], "detail": panel["detail"], "status": panel["status"], "tone": "amber"} for panel in _build_lab_panels()]
    return render(
        request,
        "veterinary_dashboard/workspace_page.html",
        _build_workspace_page_context(
            request,
            page_title="Veterinary Labs | CowCalving",
            page_eyebrow="Lab reviews",
            page_heading="Review lab results",
            page_intro="Interpret results before sharing them.",
            page_focus={"label": "Labs", "title": "Review first, share second", "text": "Keep sign-off in one place before results go back to the farmer.", "badges": ["Sign-off first", "Lower risk", "Clear review"]},
            page_quick_actions=[
                {"label": "Open patients", "description": "Match results to the case.", "url": reverse("veterinary_dashboard:patients")},
                {"label": "Open diagnosis", "description": "Add the findings.", "url": reverse("veterinary_dashboard:diagnosis")},
                {"label": "Open analytics", "description": "Check wider patterns.", "url": reverse("veterinary_dashboard:analytics")},
            ],
            main_section={"label": "Pending results", "title": "Reviews waiting for veterinary sign-off", "cards": lab_cards},
            support_section={"label": "Review logic", "title": "Why this page lowers cognitive load", "cards": [
                {"title": "Separate interpretation from communication", "detail": "Reviewing results in a dedicated page prevents chats and other tasks from interrupting analysis.", "status": "Cleaner judgment", "tone": "navy"},
                {"title": "Keep the queue visible", "detail": "A single lab page avoids hiding result review inside unrelated patient or dashboard sections.", "status": "Focused queue", "tone": "teal"},
                {"title": "Link back into cases", "detail": "Once reviewed, labs should feed diagnosis and patient pages rather than duplicate details everywhere.", "status": "Connected workflow", "tone": "amber"},
            ]},
            extra_section={"label": "Next pages", "title": "What usually follows lab review", "cards": [
                {"title": "Diagnosis", "detail": "Update the clinical note based on the reviewed result.", "url": reverse("veterinary_dashboard:diagnosis")},
                {"title": "Patient files", "detail": "Attach the result to the active case context.", "url": reverse("veterinary_dashboard:patients")},
                {"title": "Telehealth", "detail": "Communicate the reviewed result back to the farmer when appropriate.", "url": reverse("veterinary_dashboard:telehealth")},
            ]},
        ),
    )


@login_required
@role_required("veterinary")
def telehealth_view(request):
    chat_cards = [{"title": item["farmer"], "detail": item["message"], "meta": item["time"], "tone": "navy"} for item in _build_telehealth_updates()]
    return render(
        request,
        "veterinary_dashboard/workspace_page.html",
        _build_workspace_page_context(
            request,
            page_title="Veterinary Telehealth | CowCalving",
            page_eyebrow="Telehealth",
            page_heading="Handle remote support clearly",
            page_intro="Keep messages separate from operational overview.",
            page_focus={"label": "Telehealth", "title": "Move from message to action quickly", "text": "Use this page for remote support, then step into the next clinical workflow.", "badges": ["Remote first", "Fast handoff", "Clear next action"]},
            page_quick_actions=[
                {"label": "Open patients", "description": "Open the clinical file.", "url": reverse("veterinary_dashboard:patients")},
                {"label": "Open diagnosis", "description": "Record the outcome.", "url": reverse("veterinary_dashboard:diagnosis")},
                {"label": "Open Rx workflow", "description": "Issue the care plan.", "url": reverse("veterinary_dashboard:prescriptions")},
            ],
            main_section={"label": "Recent updates", "title": "Remote messages and urgent farmer context", "cards": chat_cards},
            support_section={"label": "Communication rule", "title": "How to keep telehealth lighter", "cards": [
                {"title": "Do not mix chats into the dashboard home", "detail": "The overview should only point to urgent communication, not display entire conversation threads.", "status": "Less overload", "tone": "navy"},
                {"title": "Use quick handoffs", "detail": "Every conversation should connect cleanly to patient, diagnosis, or prescription work.", "status": "Workflow-ready", "tone": "teal"},
                {"title": "Highlight time-sensitive messages", "detail": "Urgent remote cases deserve strong priority treatment without burying routine conversations.", "status": "Triage support", "tone": "rose"},
            ]},
            extra_section={"label": "Connected pages", "title": "Where telehealth usually leads next", "cards": [
                {"title": "Schedule", "detail": "Convert an urgent message into a real visit plan.", "url": reverse("veterinary_dashboard:schedule")},
                {"title": "Patients", "detail": "Attach remote findings to the patient file.", "url": reverse("veterinary_dashboard:patients")},
                {"title": "Prescriptions", "detail": "Send treatment instructions after the conversation is complete.", "url": reverse("veterinary_dashboard:prescriptions")},
            ]},
        ),
    )


@login_required
@role_required("veterinary")
def analytics_view(request):
    analytic_cards = [{"title": item["label"], "detail": item["value"], "tone": item["tone"], "progress_width": item["width"]} for item in _build_analytics_bars()]
    farm_cards = [{"title": farm["name"], "detail": farm["detail"], "status": farm["risk"], "tone": farm["tone"], "progress_width": f"{farm['risk_percent']}%"} for farm in _build_farm_overview()]
    return render(
        request,
        "veterinary_dashboard/workspace_page.html",
        _build_workspace_page_context(
            request,
            page_title="Veterinary Analytics | CowCalving",
            page_eyebrow="Analytics",
            page_heading="Review trends separately",
            page_intro="Keep pattern review away from day-of triage.",
            page_focus={"label": "Analytics", "title": "See patterns without dashboard noise", "text": "Use this page for trends and planning, not live operational work.", "badges": ["Trend only", "Population view", "Planning support"]},
            page_quick_actions=[
                {"label": "Open farms", "description": "Return to assigned farms.", "url": reverse("veterinary_dashboard:farms")},
                {"label": "Open labs", "description": "Check diagnostic review.", "url": reverse("veterinary_dashboard:labs")},
                {"label": "Open dashboard", "description": "Return to day-of work.", "url": reverse("veterinary_dashboard:dashboard")},
            ],
            main_section={"label": "Disease trends", "title": "Signals worth tracking", "cards": analytic_cards},
            support_section={"label": "Farm risk", "title": "How the patterns connect to assigned farms", "cards": farm_cards},
            extra_section={"label": "Why this page matters", "title": "The professional value of separate analytics", "cards": [
                {"title": "Better prioritization", "detail": "Separate trends from triage so urgent work stays urgent and planning stays strategic."},
                {"title": "Cleaner executive view", "detail": "This page is easier to share or demo because it groups insights in one professional surface."},
                {"title": "Ready for future live data", "detail": "Once real metrics arrive, this page can grow without expanding the home dashboard again."},
            ]},
        ),
    )
