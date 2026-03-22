from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse

from users.permissions import role_required
from users.services import get_or_create_profile


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
    return readiness_items, completed_items, readiness_percent


def _build_farmer_navigation():
    return [
        {
            "label": "Overview",
            "description": "Dashboard summary and key entry points.",
            "url": reverse("farmers_dashboard:dashboard"),
            "view_name": "farmers_dashboard:dashboard",
        },
        {
            "label": "Herd",
            "description": "Animal records layout and herd tracking sections.",
            "url": reverse("farmers_dashboard:herd"),
            "view_name": "farmers_dashboard:herd",
        },
        {
            "label": "Alerts",
            "description": "Priority issues, reminders, and follow-up flow.",
            "url": reverse("farmers_dashboard:alerts"),
            "view_name": "farmers_dashboard:alerts",
        },
        {
            "label": "Reports",
            "description": "Performance summaries and trend presentation.",
            "url": reverse("farmers_dashboard:reports"),
            "view_name": "farmers_dashboard:reports",
        },
    ]


def _build_workspace_links():
    return [
        {
            "label": "Edit profile",
            "description": "Update personal and farm identity details.",
            "url": reverse("users:profile_edit"),
        },
        {
            "label": "AI workspace",
            "description": "Open the shared assistant workspace.",
            "url": reverse("cow_calving_ai:index"),
        },
        {
            "label": "Support hub",
            "description": "Jump to public help and escalation guidance.",
            "url": reverse("Core_Web:support"),
        },
    ]


def _build_farmer_summary_cards(profile, readiness_percent, completed_items):
    return [
        {
            "label": "Workspace setup",
            "value": f"{readiness_percent}%",
            "detail": f"{completed_items} of 4 essential profile fields saved.",
            "tone": "emerald",
        },
        {
            "label": "Farmer pages",
            "value": "4",
            "detail": "Overview, herd, alerts, and reports are now split out.",
            "tone": "amber",
        },
        {
            "label": "Current role",
            "value": profile.role.name if profile.role else "Farmer",
            "detail": "Role-aware routing remains attached to this workspace.",
            "tone": "sky",
        },
        {
            "label": "Connected tools",
            "value": "3",
            "detail": "Profile, AI workspace, and support stay one click away.",
            "tone": "slate",
        },
    ]


def _build_herd_preview_cards():
    # The farmer app does not have herd models yet, so these cards are a
    # layout preview for the eventual live records screens.
    return [
        {
            "name": "Bella 004",
            "breed": "Friesian",
            "status": "Milking well",
            "status_tone": "emerald",
            "detail": "Latest yield placeholder: 18.4 L",
            "supporting_text": "Use this card pattern for daily production, notes, and next checks.",
        },
        {
            "name": "Daisy 007",
            "breed": "Sahiwal",
            "status": "Due soon",
            "status_tone": "amber",
            "detail": "Expected calving placeholder: 26 Mar",
            "supporting_text": "Reserve this surface for calving watch, checklists, and vet follow-up.",
        },
        {
            "name": "Rosa 011",
            "breed": "Ayrshire",
            "status": "Needs review",
            "status_tone": "rose",
            "detail": "Alert placeholder: labour monitoring",
            "supporting_text": "This slot can highlight urgent cases without mixing them into every page.",
        },
        {
            "name": "Mable 022",
            "breed": "Jersey",
            "status": "Breeding plan",
            "status_tone": "sky",
            "detail": "Follow-up placeholder: insemination history",
            "supporting_text": "Keep breeding entries separated from milk logs for easier scanning.",
        },
    ]


def _build_alert_preview_cards():
    return [
        {
            "level": "Urgent",
            "title": "Calving monitor needs fast follow-up",
            "detail": "Use a high-emphasis alert card here for labour progress, time checks, and next actions.",
            "action_label": "Open support guidance",
            "action_url": reverse("Core_Web:support"),
            "tone": "rose",
        },
        {
            "level": "Attention",
            "title": "Production change review",
            "detail": "This card style works for milk-drop investigations, mastitis screening, or feeding checks.",
            "action_label": "Open reports page",
            "action_url": reverse("farmers_dashboard:reports"),
            "tone": "amber",
        },
        {
            "level": "Planned",
            "title": "Vaccination reminder slot",
            "detail": "Keep lower-pressure reminders visible without giving them the same weight as urgent items.",
            "action_label": "Ask the AI workspace",
            "action_url": reverse("cow_calving_ai:index"),
            "tone": "emerald",
        },
    ]


def _build_report_highlights():
    return [
        {
            "label": "Milk trend",
            "value": "Layout ready",
            "detail": "Weekly and monthly charts can live in one reporting surface.",
        },
        {
            "label": "Herd ranking",
            "value": "Top performers",
            "detail": "Leaderboards help farmers spot the strongest animals quickly.",
        },
        {
            "label": "Breeding view",
            "value": "Summary cards",
            "detail": "Conception and expected-calving indicators belong here, not on the home page.",
        },
    ]


def _build_report_bars():
    return [
        {"label": "Mon", "height_class": "h-24"},
        {"label": "Tue", "height_class": "h-28"},
        {"label": "Wed", "height_class": "h-20"},
        {"label": "Thu", "height_class": "h-32"},
        {"label": "Fri", "height_class": "h-36"},
        {"label": "Sat", "height_class": "h-28"},
        {"label": "Sun", "height_class": "h-40"},
    ]


def _build_report_leaderboard():
    return [
        {"name": "Bella 004", "detail": "Friesian | Milking", "value": "19.2 L"},
        {"name": "Daisy 007", "detail": "Sahiwal | Due soon", "value": "18.5 L"},
        {"name": "Cleo 003", "detail": "Ayrshire | Milking", "value": "16.0 L"},
    ]


def _build_farmer_dashboard_context(
    request,
    *,
    page_title,
    page_eyebrow,
    page_heading,
    page_intro,
):
    profile = get_or_create_profile(request.user)
    readiness_items, completed_items, readiness_percent = _build_profile_readiness(
        request.user,
        profile,
    )
    return {
        "dashboard_home_url": reverse("farmers_dashboard:dashboard"),
        "profile": profile,
        "page_title": page_title,
        "page_eyebrow": page_eyebrow,
        "page_heading": page_heading,
        "page_intro": page_intro,
        "farmer_navigation": _build_farmer_navigation(),
        "workspace_links": _build_workspace_links(),
        "summary_cards": _build_farmer_summary_cards(
            profile,
            readiness_percent,
            completed_items,
        ),
        "profile_readiness_items": readiness_items,
        "profile_readiness_percent": readiness_percent,
        "herd_preview_cards": _build_herd_preview_cards(),
        "alert_preview_cards": _build_alert_preview_cards(),
        "report_highlights": _build_report_highlights(),
        "report_bars": _build_report_bars(),
        "report_leaderboard": _build_report_leaderboard(),
    }


@login_required
@role_required("farmer")
def dashboard_view(request):
    return render(
        request,
        "farmers_dashboard/dashboard.html",
        _build_farmer_dashboard_context(
            request,
            page_title="Farmer Dashboard | CowCalving",
            page_eyebrow="Farmer workspace",
            page_heading="A cleaner dashboard for daily farm work",
            page_intro=(
                "The farmer area now uses focused pages instead of one long "
                "template, making the structure easier to grow and easier to "
                "understand."
            ),
        ),
    )


@login_required
@role_required("farmer")
def herd_view(request):
    return render(
        request,
        "farmers_dashboard/herd.html",
        _build_farmer_dashboard_context(
            request,
            page_title="Herd Workspace | CowCalving",
            page_eyebrow="Herd records",
            page_heading="Organize animal information in one clear place",
            page_intro=(
                "This page gives the farmer app a dedicated herd records "
                "surface so future cow profiles, production logs, and "
                "breeding history do not all compete on the dashboard home."
            ),
        ),
    )


@login_required
@role_required("farmer")
def alerts_view(request):
    return render(
        request,
        "farmers_dashboard/alerts.html",
        _build_farmer_dashboard_context(
            request,
            page_title="Farmer Alerts | CowCalving",
            page_eyebrow="Alerts center",
            page_heading="Keep urgent actions visible and separated",
            page_intro=(
                "Alerts now live on their own page, which leaves the overview "
                "lighter and gives urgent cases a more intentional layout."
            ),
        ),
    )


@login_required
@role_required("farmer")
def reports_view(request):
    return render(
        request,
        "farmers_dashboard/reports.html",
        _build_farmer_dashboard_context(
            request,
            page_title="Farmer Reports | CowCalving",
            page_eyebrow="Reports and trends",
            page_heading="Present farm performance in a professional way",
            page_intro=(
                "The reports page now gives trend charts, rankings, and "
                "summary cards their own dedicated home instead of crowding "
                "the main dashboard."
            ),
        ),
    )
