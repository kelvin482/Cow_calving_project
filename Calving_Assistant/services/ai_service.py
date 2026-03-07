import os


def get_ai_max_tokens(default: int = 900) -> int:
    raw = (os.getenv("AI_MAX_TOKENS", str(default)) or "").strip()
    try:
        value = int(raw)
    except ValueError:
        return default

    if value < 200:
        return 200
    if value > 4000:
        return 4000
    return value


def build_prompt(question: str, cow_id: str | None = None) -> str:
    cleaned_question = (question or "").strip()
    if not cleaned_question:
        raise ValueError("Question cannot be empty.")

    if cow_id:
        return (
            "You are a livestock assistant for cow calving support. "
            f"Cow ID: {cow_id}. "
            f"Question: {cleaned_question}"
        )

    return (
        "You are a livestock assistant for cow calving support. "
        f"Question: {cleaned_question}"
    )


def get_ai_provider() -> str:
    return os.getenv("AI_PROVIDER", "stub").strip().lower()


def _github_models_advice(prompt: str) -> str:
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Set GITHUB_TOKEN to use AI_PROVIDER=github_models.")

    model = os.getenv("GITHUB_MODEL", "openai/gpt-4o-mini").strip()
    base_url = os.getenv(
        "GITHUB_MODELS_BASE_URL", "https://models.github.ai/inference"
    ).strip()

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install the OpenAI SDK: pip install openai") from exc

    client = OpenAI(base_url=base_url, api_key=token)
    response = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a veterinary assistant specialized in cow calving "
                    "support. Give practical, concise, farm-friendly guidance."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        model=model,
        temperature=1,
        max_tokens=get_ai_max_tokens(),
        top_p=1,
    )

    content = (response.choices[0].message.content or "").strip()
    if not content:
        raise RuntimeError("AI provider returned an empty response.")

    return content


def _openrouter_advice(prompt: str) -> str:
    token = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not token:
        raise RuntimeError("Set OPENROUTER_API_KEY to use AI_PROVIDER=openrouter.")

    model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini").strip()
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()
    site_url = os.getenv("OPENROUTER_SITE_URL", "").strip()
    site_name = os.getenv("OPENROUTER_SITE_NAME", "").strip()

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install the OpenAI SDK: pip install openai") from exc

    headers = {}
    if site_url:
        headers["HTTP-Referer"] = site_url
    if site_name:
        headers["X-OpenRouter-Title"] = site_name

    client_kwargs = {"base_url": base_url, "api_key": token}
    if headers:
        client_kwargs["default_headers"] = headers

    client = OpenAI(**client_kwargs)
    response = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a veterinary assistant specialized in cow calving "
                    "support. Give practical, concise, farm-friendly guidance."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        model=model,
        temperature=1,
        max_tokens=get_ai_max_tokens(),
        top_p=1,
    )

    content = (response.choices[0].message.content or "").strip()
    if not content:
        raise RuntimeError("AI provider returned an empty response.")

    return content


def get_ai_advice(question: str, cow_id: str | None = None) -> str:
    """
    Returns AI advice using a safe local stub mode by default.

    To avoid unreliable behavior in development/tests, the default provider is
    `stub`. Real provider integration can be added behind this same interface.
    """
    provider = get_ai_provider()
    prompt = build_prompt(question=question, cow_id=cow_id)

    if provider == "stub":
        return f"Stub AI response: review this case carefully. Prompt='{prompt}'"
    if provider in {"github_models", "github"}:
        return _github_models_advice(prompt)
    if provider in {"openrouter", "open_router"}:
        return _openrouter_advice(prompt)

    raise RuntimeError(
        "Unsupported AI_PROVIDER. Use AI_PROVIDER=stub, "
        "AI_PROVIDER=github_models, or AI_PROVIDER=openrouter."
    )
