from django.http import JsonResponse
from django.shortcuts import render

from .services.ai_service import get_ai_advice, get_ai_provider


def index(request):
    return render(
        request,
        'Calving_Assistant/index.html',
        {"provider": get_ai_provider()},
    )


def ai_test(request):
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
