import os
import re
from pathlib import Path


_POLICY_CACHE: dict[str, object] = {"path": None, "mtime": None, "text": None}


def get_ai_max_tokens(default: int = 650) -> int:
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


def _get_policy_path() -> Path:
    env_path = (os.getenv("AI_POLICY_PATH", "") or "").strip()
    if env_path:
        return Path(env_path)
    app_root = Path(__file__).resolve().parents[1]
    return app_root / "policies" / "website_guides.md"


def _get_policy_enabled() -> bool:
    raw = (os.getenv("AI_POLICY_ENABLED", "true") or "").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _get_policy_max_chars(default: int = 1800) -> int:
    raw = (os.getenv("AI_POLICY_MAX_CHARS", str(default)) or "").strip()
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(200, min(value, 6000))


def _load_policy_text() -> str:
    if not _get_policy_enabled():
        return ""

    policy_path = _get_policy_path()
    try:
        mtime = policy_path.stat().st_mtime
    except FileNotFoundError:
        return ""

    cache_path = _POLICY_CACHE.get("path")
    cache_mtime = _POLICY_CACHE.get("mtime")
    if cache_path == policy_path and cache_mtime == mtime:
        cached = _POLICY_CACHE.get("text")
        if isinstance(cached, str):
            return cached

    text = policy_path.read_text(encoding="utf-8", errors="ignore")
    # Normalize whitespace to reduce tokens while preserving meaning.
    text = "\n".join(line.rstrip() for line in text.splitlines())
    text = "\n".join([line for line in text.split("\n") if line.strip() != ""])
    max_chars = _get_policy_max_chars()
    if len(text) > max_chars:
        text = text[: max_chars - 3].rstrip() + "..."

    _POLICY_CACHE["path"] = policy_path
    _POLICY_CACHE["mtime"] = mtime
    _POLICY_CACHE["text"] = text
    return text


def _build_system_message() -> str:
    base = (
        "You are Cow Calving AI, a veterinary assistant for cow calving support. "
        "Give practical, concise, farm-friendly guidance."
    )
    policy_text = _load_policy_text()
    if not policy_text:
        return base
    return f"{base}\n\nPolicy:\n{policy_text}"


def _extract_affordable_token_limit(error: Exception) -> int | None:
    message = str(error)
    match = re.search(r"can only afford\s+(\d+)", message, re.IGNORECASE)
    if not match:
        return None
    try:
        affordable = int(match.group(1))
    except ValueError:
        return None
    if affordable < 200:
        return 200
    return min(affordable, 4000)


def _create_chat_completion_with_credit_fallback(client, *, messages, model):
    max_tokens = get_ai_max_tokens()
    request_kwargs = {
        "messages": messages,
        "model": model,
        "temperature": 1,
        "max_tokens": max_tokens,
        "top_p": 1,
    }
    try:
        return client.chat.completions.create(**request_kwargs)
    except Exception as exc:
        affordable_limit = _extract_affordable_token_limit(exc)
        if affordable_limit is None or affordable_limit >= max_tokens:
            raise

        request_kwargs["max_tokens"] = affordable_limit
        return client.chat.completions.create(**request_kwargs)


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
    response = _create_chat_completion_with_credit_fallback(
        client,
        messages=[
            {
                "role": "system",
                "content": _build_system_message(),
            },
            {"role": "user", "content": prompt},
        ],
        model=model,
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
    response = _create_chat_completion_with_credit_fallback(
        client,
        messages=[
            {
                "role": "system",
                "content": _build_system_message(),
            },
            {"role": "user", "content": prompt},
        ],
        model=model,
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
