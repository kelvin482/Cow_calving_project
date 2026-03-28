import calendar
from statistics import fmean
from collections import defaultdict
from django.http import Http404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
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
from users.services import get_dashboard_url_for_user, get_profile


KENYA_MAP_CENTER = {"lat": -0.023559, "lng": 37.906193}


def _build_navigation_sections(
    unread_message_count=0,
    unread_notification_count=0,
    urgent_case_count=None,
    farm_count=None,
):
    if urgent_case_count is None:
        urgent_case_count = sum(
            1 for item in _build_patient_records() if item["tone"] == "rose"
        )
    if farm_count is None:
        farm_count = len(_build_farm_overview())
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
                    "label": "Schedule",
                    "url": reverse("veterinary_dashboard:schedule"),
                    "view_name": "veterinary_dashboard:schedule",
                    "icon": "schedule",
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
                    "label": "Medical Records",
                    "url": reverse("veterinary_dashboard:medical_records"),
                    "view_name": "veterinary_dashboard:medical_records",
                    "icon": "records",
                    "badge": str(farm_count) if farm_count else None,
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


def _build_summary_cards(farm_overview, overview_cases, schedule_rows):
    total_cows = sum(farm["cow_count"] for farm in farm_overview)
    urgent_cases = sum(1 for item in overview_cases if item["tone"] == "rose")
    return [
        {
            "label": "Farms on route",
            "value": str(len(farm_overview)),
            "detail": "Farms scheduled for active follow-up",
            "tone": "navy",
            "icon": "farms",
        },
        {
            "label": "Animals under review",
            "value": str(total_cows),
            "detail": "Cases being tracked across assigned herds",
            "tone": "teal",
            "icon": "cows",
        },
        {
            "label": "Same-day reviews",
            "value": str(urgent_cases),
            "detail": "Clinical cases needing a same-day decision",
            "tone": "amber",
            "icon": "alert",
        },
        {
            "label": "Booked visits",
            "value": str(len(schedule_rows)),
            "detail": "Field visits planned for today",
            "tone": "rose",
            "icon": "schedule",
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
                "primary_url": reverse("veterinary_dashboard:medical_records"),
                "primary_label": "Open records",
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
                "primary_url": reverse("veterinary_dashboard:farm_map"),
                "primary_label": "Open map",
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


def _build_overview_case_rows(records=None):
    case_flags = {
        "rose": "Respond now",
        "amber": "Monitor",
        "navy": "Review",
    }
    rows = []
    for record in records or _build_patient_records():
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
            "time": "Today - 08:00",
            "farmer": "John O.",
            "location": "Zone A, Plot 12",
            "service": "Labour follow-up",
            "service_tone": "rose",
            "farm": "Moi Farm",
            "visit_type": "Pre-calving check",
            "detail": "Rosa #011",
        },
        {
            "time": "Today - 10:30",
            "farmer": "Mary W.",
            "location": "Zone B, Plot 4",
            "service": "Vaccination run",
            "service_tone": "teal",
            "farm": "Green Acres",
            "visit_type": "Vaccination run",
            "detail": "8 cows",
        },
        {
            "time": "Today - 14:00",
            "farmer": "Peter K.",
            "location": "Zone C, Plot 7",
            "service": "Health check",
            "service_tone": "amber",
            "farm": "Sunrise Dairy",
            "visit_type": "Follow-up check",
            "detail": "Daisy #003",
        },
    ]


def _build_dashboard_quick_links():
    return [
        {
            "label": "Farm map",
            "description": "Open the geographic route view when distance and order matter more than the summary.",
            "url": reverse("veterinary_dashboard:farm_map"),
        },
        {
            "label": "Medical records",
            "description": "Review farm-level cow files, breeding details, and treatment history in one place.",
            "url": reverse("veterinary_dashboard:medical_records"),
        },
        {
            "label": "Messages",
            "description": "Open the farmer inbox when the next action is a reply rather than a visit.",
            "url": reverse("veterinary_dashboard:messages"),
        },
    ]


def _build_dashboard_alerts(records=None):
    alert_titles = {
        "rose": "Urgent calving case needs review",
        "amber": "Treatment follow-up is due soon",
        "navy": "Lab sign-off is still pending",
    }
    alert_badges = {
        "rose": "Now",
        "amber": "Today",
        "navy": "Review",
    }
    alerts = []
    for record in (records or _build_patient_records())[:3]:
        alerts.append(
            {
                "title": alert_titles.get(record["tone"], record["status"]),
                "detail": f"{record['farm']} - {record['name']} - {record['issue']}.",
                "meta": record["next_step"],
                "badge": alert_badges.get(record["tone"], record["priority_label"]),
                "tone": record["tone"],
            }
        )
    return alerts


def _build_dashboard_message_preview():
    return {
        "farmer_name": "John Otieno",
        "inbox_url": reverse("veterinary_dashboard:messages"),
        "messages": [
            {
                "sender": "farmer",
                "text": "Farmer John: Bella has been showing standing heat since early morning.",
            },
            {
                "sender": "vet",
                "text": "I can see Bella at 10 AM. I am sending the visit confirmation now.",
            },
        ],
    }


def _build_dashboard_trend_points():
    return {
        "range_label": "6 months",
        "summary": "Follow-up completion trend for breeding checks, treatment reviews, and herd revisit work.",
        "points": [
            {"label": "Jan", "value": 34},
            {"label": "Feb", "value": 42},
            {"label": "Mar", "value": 39},
            {"label": "Apr", "value": 56},
            {"label": "May", "value": 48},
            {"label": "Jun", "value": 61},
        ],
    }


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


def _build_medical_record_workspace():
    def short_record_type(label):
        label_lower = label.lower()
        if "treatment" in label_lower:
            return "Treatment"
        if "delivery" in label_lower or "labour" in label_lower:
            return "Delivery"
        if "lab" in label_lower or "sample" in label_lower:
            return "Lab"
        if "image" in label_lower:
            return "Image"
        if "follow" in label_lower or "review" in label_lower:
            return "Follow-up"
        return "Clinical note"

    farms = [
        {
            "id": "moi-farm",
            "name": "Moi Farm",
            "owner": "John Otieno",
            "location": "Kisii",
            "region": "South Rift",
            "owner_code": "ID: F001",
            "contact_phone": "+254 700 210 114",
            "herd_size": 42,
            "conception_rate": 68,
            "farm_status": "High priority",
            "tone": "rose",
            "active_case_count": 3,
            "affected_cow_count": 3,
            "latest_update": "Today 10:20",
            "summary": "One labour case is still open and two linked follow-up records need review before the farmer is updated.",
            "relationship_note": "Open the farm first, then pick the cow with the clearest next action.",
            "next_action": "Confirm Rosa's delivery outcome, then close the linked Bella and Nuru follow-ups.",
            "cows": [
                {
                    "id": "rosa-011",
                    "name": "Rosa #011",
                    "tag": "#011",
                    "breed": "Ayrshire",
                    "cow_number": "MC-011",
                    "location_detail": "North pasture pen 2",
                    "insemination_date": "22 Jun 2025",
                    "insemination_type": "Natural service follow-up",
                    "expected_calving_date": "31 Mar 2026",
                    "problem": "Labour follow-up",
                    "status": "Open case",
                    "tone": "rose",
                    "last_update": "Today 10:20",
                    "photo_url": static("Core_Web/images/cow and calf.jpg"),
                    "photo_alt": "Cow and calf resting after delivery",
                    "summary": "Active labour case with escalation already noted in telehealth.",
                    "next_step": "Visit first and record the delivery outcome.",
                    "records": [
                        {
                            "label": "Timeline note",
                            "time": "Today 08:04",
                            "title": "Farmer reported prolonged labour",
                            "detail": "Contractions stalled after the water bag was seen, so the case was moved into the urgent queue.",
                        },
                        {
                            "label": "Intervention",
                            "time": "Today 09:15",
                            "title": "Remote escalation completed",
                            "detail": "Vet advised isolation, clean bedding, and immediate physical review if progress stayed slow.",
                        },
                        {
                            "label": "Next action",
                            "time": "Now",
                            "title": "Capture delivery outcome",
                            "detail": "Update the case note with calf viability, retained placenta risk, and any medication given.",
                        },
                    ],
                },
                {
                    "id": "bella-004",
                    "name": "Bella #004",
                    "tag": "#004",
                    "breed": "Friesian",
                    "cow_number": "MC-004",
                    "location_detail": "Milking block A",
                    "insemination_date": "12 Jul 2025",
                    "insemination_type": "Artificial insemination",
                    "expected_calving_date": "19 Apr 2026",
                    "problem": "Treatment renewal",
                    "status": "Follow-up",
                    "tone": "amber",
                    "last_update": "18 Mar",
                    "photo_url": static("Core_Web/images/286aa99925f3186fc15680800fa372e6.jpg"),
                    "photo_alt": "Friesian cow standing in a farm pen",
                    "summary": "Mastitis medication review is waiting for symptom confirmation before renewal.",
                    "next_step": "Re-check udder heat, milk appearance, and appetite before renewing treatment.",
                    "records": [
                        {
                            "label": "Treatment note",
                            "time": "16 Mar",
                            "title": "Initial mastitis treatment logged",
                            "detail": "Farmer recorded a full intramammary course and early improvement after two doses.",
                        },
                        {
                            "label": "Follow-up",
                            "time": "18 Mar",
                            "title": "Renewal request pending review",
                            "detail": "The farmer requested a refill, but the plan says renew only if symptoms persist.",
                        },
                    ],
                },
                {
                    "id": "nuru-025",
                    "name": "Nuru #025",
                    "tag": "#025",
                    "breed": "Ayrshire",
                    "cow_number": "MC-025",
                    "location_detail": "Isolation shed 1",
                    "insemination_date": "03 Aug 2025",
                    "insemination_type": "Artificial insemination",
                    "expected_calving_date": "11 May 2026",
                    "problem": "Lab review",
                    "status": "Lab linked",
                    "tone": "navy",
                    "last_update": "20 Mar",
                    "photo_url": static("Core_Web/images/1490fe2cbb1e219d53027e4d8c7cf644.jpg"),
                    "photo_alt": "Cow in a field ready for health review",
                    "summary": "CBC and milk panel are uploaded but still waiting for vet sign-off.",
                    "next_step": "Interpret the abnormal cells and share guidance with the farmer today.",
                    "records": [
                        {
                            "label": "Sample log",
                            "time": "19 Mar",
                            "title": "Milk and CBC samples collected",
                            "detail": "Samples were taken after reduced milk yield and mild fever were reported.",
                        },
                        {
                            "label": "Lab summary",
                            "time": "20 Mar",
                            "title": "Results linked to medical file",
                            "detail": "The report is attached, but the farmer summary must wait for clinical sign-off.",
                        },
                    ],
                },
            ],
        },
        {
            "id": "sunrise-dairy",
            "name": "Sunrise Dairy",
            "owner": "Peter Kamau",
            "location": "Nyandarua",
            "region": "Central Highlands",
            "owner_code": "ID: F002",
            "contact_phone": "+254 700 118 522",
            "herd_size": 56,
            "conception_rate": 74,
            "farm_status": "Needs review",
            "tone": "amber",
            "active_case_count": 2,
            "affected_cow_count": 2,
            "latest_update": "Yesterday 16:40",
            "summary": "Two cows need a fast review, but neither case looks unstable enough to crowd the live case page.",
            "relationship_note": "Use the farm view to compare the two affected cows before deciding which record to reopen.",
            "next_action": "Check Daisy first for mastitis severity, then review Pendo's calving recovery note.",
            "cows": [
                {
                    "id": "daisy-003",
                    "name": "Daisy #003",
                    "tag": "#003",
                    "breed": "Friesian",
                    "cow_number": "SD-003",
                    "location_detail": "East dairy line 4",
                    "insemination_date": "29 Jul 2025",
                    "insemination_type": "Timed AI",
                    "expected_calving_date": "06 May 2026",
                    "problem": "Suspected mastitis",
                    "status": "Needs review",
                    "tone": "amber",
                    "last_update": "Yesterday 14:00",
                    "photo_url": static("Core_Web/images/a7938517ea1668247cd5f0170c0b23e4.jpg"),
                    "photo_alt": "Cow in a livestock stall",
                    "summary": "The farmer described clots during milking, and the last check suggested a same-day review.",
                    "next_step": "Confirm signs during the next health check and update the treatment plan.",
                    "records": [
                        {
                            "label": "Farmer note",
                            "time": "Yesterday 11:40",
                            "title": "Milk changes reported",
                            "detail": "The farmer noticed clots and a reduced yield in the left rear quarter.",
                        },
                        {
                            "label": "Review plan",
                            "time": "Yesterday 14:00",
                            "title": "Same-day udder assessment advised",
                            "detail": "The record recommends a physical check before any antibiotic renewal is sent.",
                        },
                    ],
                },
                {
                    "id": "pendo-019",
                    "name": "Pendo #019",
                    "tag": "#019",
                    "breed": "Jersey Cross",
                    "cow_number": "SD-019",
                    "location_detail": "Calving yard pen 1",
                    "insemination_date": "18 Jun 2025",
                    "insemination_type": "Artificial insemination",
                    "expected_calving_date": "27 Mar 2026",
                    "problem": "Post-calving recovery",
                    "status": "Follow-up",
                    "tone": "emerald",
                    "last_update": "22 Mar",
                    "photo_url": static("Core_Web/images/00ac73aa5aaaecf17fae41d83e028216.jpg"),
                    "photo_alt": "Brown dairy cow in an open pen",
                    "summary": "Recovery is stable, but the farm asked for a quick check on appetite and calf nursing.",
                    "next_step": "Review recovery notes and close the follow-up if feeding remains normal.",
                    "records": [
                        {
                            "label": "Delivery record",
                            "time": "21 Mar",
                            "title": "Calving outcome entered",
                            "detail": "The delivery note was clean, with no retained placenta or calf distress recorded.",
                        },
                        {
                            "label": "Follow-up",
                            "time": "22 Mar",
                            "title": "Recovery check opened",
                            "detail": "The farmer asked whether reduced appetite on the first day required extra treatment.",
                        },
                    ],
                },
            ],
        },
        {
            "id": "green-valley",
            "name": "Green Valley Farm",
            "owner": "Mary Njeri",
            "location": "Nakuru",
            "region": "Rift Valley North",
            "owner_code": "ID: F003",
            "contact_phone": "+254 700 884 301",
            "herd_size": 18,
            "conception_rate": 81,
            "farm_status": "Lab pending",
            "tone": "navy",
            "active_case_count": 1,
            "affected_cow_count": 1,
            "latest_update": "21 Mar",
            "summary": "Only one cow is open here, so the farm panel should make it obvious that this is a quick lab review.",
            "relationship_note": "This farm only has one affected cow, so the vet should move from farm to record in one short path.",
            "next_action": "Read the image-backed wound note, then confirm whether the lab result changes treatment.",
            "cows": [
                {
                    "id": "amani-014",
                    "name": "Amani #014",
                    "tag": "#014",
                    "breed": "Sahiwal Cross",
                    "cow_number": "GV-014",
                    "location_detail": "South grazing unit 3",
                    "insemination_date": "09 Aug 2025",
                    "insemination_type": "Heat-synced AI",
                    "expected_calving_date": "17 May 2026",
                    "problem": "Wound and infection review",
                    "status": "Lab pending",
                    "tone": "navy",
                    "last_update": "21 Mar",
                    "photo_url": static("Core_Web/images/download (1).png"),
                    "photo_alt": "Clinical image used for follow-up review",
                    "summary": "The farm uploaded a wound image and a pending culture request for treatment confirmation.",
                    "next_step": "Compare the wound image with the last dressing note before sending advice.",
                    "records": [
                        {
                            "label": "Image note",
                            "time": "20 Mar",
                            "title": "Farmer uploaded wound photo",
                            "detail": "The image was attached to confirm swelling around the treated area.",
                        },
                        {
                            "label": "Lab request",
                            "time": "21 Mar",
                            "title": "Culture request linked",
                            "detail": "The record is waiting for confirmation before treatment is changed.",
                        },
                    ],
                },
            ],
        },
    ]

    farms.sort(key=lambda farm: farm["name"].lower())

    for farm in farms:
        farm["cover_photo_url"] = farm["cows"][0]["photo_url"]
        farm["cover_photo_alt"] = farm["cows"][0]["photo_alt"]
        farm["record_count"] = sum(len(cow["records"]) for cow in farm["cows"])
        for cow in farm["cows"]:
            cow["current_record"] = cow["records"][0]
            for record in cow["records"]:
                record["type"] = short_record_type(record["label"])
                record["date"] = record["time"]

    total_cows = sum(len(farm["cows"]) for farm in farms)
    total_records = sum(len(cow["records"]) for farm in farms for cow in farm["cows"])
    return {
        "farms": farms,
        "summary": {
            "farm_count": len(farms),
            "active_case_count": sum(farm["active_case_count"] for farm in farms),
            "affected_cow_count": total_cows,
            "record_count": total_records,
        },
    }


def _build_common_context(
    request,
    *,
    page_title,
    page_eyebrow,
    page_heading,
    page_intro,
    navigation_counts=None,
):
    profile = get_profile(request.user)
    display_name = request.user.get_full_name().strip() or request.user.username
    initials = "".join(part[0].upper() for part in display_name.split()[:2] if part) or "VT"
    unread_message_count = get_unread_thread_count(request.user)
    unread_notification_count = get_unread_notification_count(request.user)
    navigation_counts = navigation_counts or {}
    return {
        "dashboard_home_url": get_dashboard_url_for_user(
            request.user,
            fallback="/dashboard/profile/",
            profile=profile,
        ),
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
            urgent_case_count=navigation_counts.get("urgent_case_count"),
            farm_count=navigation_counts.get("farm_count"),
        ),
        "workspace_menu_sections": _build_workspace_menu(),
        "unread_message_count": unread_message_count,
        "unread_notification_count": unread_notification_count,
        "header_primary_action": {
            "label": "New case update",
            "url": reverse("veterinary_dashboard:patients"),
        },
    }


def _build_workspace_page_context(
    request,
    *,
    page_title,
    page_eyebrow,
    page_heading,
    page_intro,
    page_focus,
    page_quick_actions,
    main_section,
    support_section=None,
    extra_section=None,
):
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
    patient_records = _build_patient_records()
    overview_case_rows = _build_overview_case_rows(patient_records)
    overview_schedule_rows = _build_overview_schedule_rows()
    farm_overview = _build_farm_overview()
    context = _build_common_context(
        request,
        page_title="Veterinary Dashboard | CowCalving",
        page_eyebrow="Clinical operations",
        page_heading="Veterinary Dashboard",
        page_intro="Track urgent work, today's visits, and pending reviews.",
        navigation_counts={
            "urgent_case_count": sum(
                1 for item in patient_records if item["tone"] == "rose"
            ),
            "farm_count": len(farm_overview),
        },
    )
    context.update(
        {
            "summary_cards": _build_summary_cards(
                farm_overview,
                overview_case_rows,
                overview_schedule_rows,
            ),
            "overview_schedule_rows": overview_schedule_rows,
            # Keep the overview data intentionally compact so the dashboard
            # stays close to the shared mockup and leaves deeper workflows for
            # dedicated pages like patients, schedule, and farms.
            "overview_case_rows": overview_case_rows,
            "dashboard_alerts": _build_dashboard_alerts(patient_records),
            "dashboard_message_preview": _build_dashboard_message_preview(),
            "dashboard_trend_points": _build_dashboard_trend_points(),
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
    workspace = _build_medical_record_workspace()
    farms = workspace["farms"]
    seed_farm = farms[0] if farms else None
    seed_cow = seed_farm["cows"][0] if seed_farm and seed_farm["cows"] else None
    seed_record = seed_cow["records"][0] if seed_cow and seed_cow["records"] else None
    context = _build_common_context(
        request,
        page_title="Veterinary Medical Records | CowCalving",
        page_eyebrow="Medical records",
        page_heading="Open a farm, then inspect one affected cow",
        page_intro="Move from active farms to affected cows to image-backed records in one short, readable flow.",
    )
    context.update(
        {
            "header_primary_action": {
                "label": "Open active case",
                "url": reverse("veterinary_dashboard:patients"),
            },
            "medical_record_summary": workspace["summary"],
            "medical_record_farms": farms,
            "medical_record_seed_farm": seed_farm,
            "medical_record_seed_cow": seed_cow,
            "medical_record_seed_record": seed_record,
            "record_support_actions": [
                {"label": "Open active case", "description": "Jump into the live case workspace when the next action becomes urgent.", "url": reverse("veterinary_dashboard:patients")},
                {"label": "Open labs", "description": "Review the full result when the short record summary is not enough.", "url": reverse("veterinary_dashboard:labs")},
                {"label": "Open farm map", "description": "Switch to the route view if the next action becomes a physical visit.", "url": reverse("veterinary_dashboard:farm_map")},
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
                {"label": "Open farm map", "description": "Return to the route view for assigned farms.", "url": reverse("veterinary_dashboard:farm_map")},
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
