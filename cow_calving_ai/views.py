from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.clickjacking import xframe_options_sameorigin

from .services.ai_service import get_ai_advice, get_ai_provider


@login_required
@xframe_options_sameorigin
def index(request):
    # The AI dashboard is the current post-login landing page, so it stays
    # behind authentication until a broader public home page is added.
    # The embedded query flag lets the dashboards load the assistant inside the
    # floating iframe without affecting the standalone full-page experience.
    embedded = request.GET.get("embedded") == "1"
    return render(
        request,
        'cow_calving_ai/index.html',
        {
            "provider": get_ai_provider(),
            "embedded": embedded,
        },
    )


@login_required
def ai_test(request):
    # Keep the test endpoint protected too so browser requests do not leak into
    # the AI demo without an authenticated session.
    question = request.GET.get("q", "").strip()
    cow_id = request.GET.get("cow_id", "").strip()

    if not question:
        return JsonResponse(
            {"ok": False, "error": "Provide a question using ?q=..."},
            status=400,
        )

    try:
        advice = get_ai_advice(question=question, cow_id=cow_id or None)
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=500)

    return JsonResponse(
        {
            "ok": True,
            "provider": get_ai_provider(),
            "question": question,
            "cow_id": cow_id or None,
            "advice": advice,
        }
    )

