import os
import sys
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

from .services.ai_service import (
    _extract_affordable_token_limit,
    build_prompt,
    get_ai_advice,
    get_ai_max_tokens,
)


class AIServiceTests(TestCase):
    def test_build_prompt_requires_question(self):
        with self.assertRaises(ValueError):
            build_prompt("")

    def test_build_prompt_with_cow_id(self):
        prompt = build_prompt("When is calving expected?", cow_id="COW-001")
        self.assertIn("COW-001", prompt)
        self.assertIn("When is calving expected?", prompt)

    def test_get_ai_advice_uses_stub(self):
        with patch.dict(os.environ, {"AI_PROVIDER": "stub"}, clear=False):
            advice = get_ai_advice("Any warning signs before calving?")
        self.assertIn("Stub AI response", advice)

    def test_get_ai_advice_github_models_requires_token(self):
        with patch.dict(os.environ, {"AI_PROVIDER": "github_models"}, clear=False):
            with patch.dict(os.environ, {"GITHUB_TOKEN": ""}, clear=False):
                with self.assertRaises(RuntimeError):
                    get_ai_advice("Test question")

    def test_get_ai_advice_github_models_success(self):
        class FakeOpenAI:
            def __init__(self, base_url, api_key):
                self.chat = SimpleNamespace(
                    completions=SimpleNamespace(create=self._create)
                )

            @staticmethod
            def _create(**kwargs):
                _ = kwargs
                return SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(content="Model response")
                        )
                    ]
                )

        fake_module = SimpleNamespace(OpenAI=FakeOpenAI)

        with patch.dict(os.environ, {"AI_PROVIDER": "github_models"}, clear=False):
            with patch.dict(os.environ, {"GITHUB_TOKEN": "test_token"}, clear=False):
                with patch.dict(sys.modules, {"openai": fake_module}):
                    advice = get_ai_advice("Is this cow near calving?")

        self.assertEqual(advice, "Model response")

    def test_get_ai_advice_openrouter_requires_token(self):
        with patch.dict(os.environ, {"AI_PROVIDER": "openrouter"}, clear=False):
            with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}, clear=False):
                with self.assertRaises(RuntimeError):
                    get_ai_advice("Test question")

    def test_get_ai_advice_openrouter_success(self):
        class FakeOpenAI:
            init_kwargs = None

            def __init__(self, **kwargs):
                FakeOpenAI.init_kwargs = kwargs
                self.chat = SimpleNamespace(
                    completions=SimpleNamespace(create=self._create)
                )

            @staticmethod
            def _create(**kwargs):
                _ = kwargs
                return SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(content="OpenRouter response")
                        )
                    ]
                )

        fake_module = SimpleNamespace(OpenAI=FakeOpenAI)

        with patch.dict(
            os.environ,
            {
                "AI_PROVIDER": "openrouter",
                "OPENROUTER_API_KEY": "test_token",
                "OPENROUTER_SITE_URL": "https://farm.example",
                "OPENROUTER_SITE_NAME": "Farm App",
            },
            clear=False,
        ):
            with patch.dict(sys.modules, {"openai": fake_module}):
                advice = get_ai_advice("Is this cow near calving?")

        self.assertEqual(advice, "OpenRouter response")
        self.assertIn("default_headers", FakeOpenAI.init_kwargs)
        self.assertEqual(
            FakeOpenAI.init_kwargs["default_headers"]["HTTP-Referer"],
            "https://farm.example",
        )
        self.assertEqual(
            FakeOpenAI.init_kwargs["default_headers"]["X-OpenRouter-Title"],
            "Farm App",
        )

    def test_get_ai_max_tokens_clamps_low_values(self):
        with patch.dict(os.environ, {"AI_MAX_TOKENS": "50"}, clear=False):
            self.assertEqual(get_ai_max_tokens(), 200)

    def test_get_ai_max_tokens_reads_valid_env_value(self):
        with patch.dict(os.environ, {"AI_MAX_TOKENS": "1200"}, clear=False):
            self.assertEqual(get_ai_max_tokens(), 1200)

    def test_extract_affordable_token_limit_reads_openrouter_402_message(self):
        error = RuntimeError(
            "This request requires more credits. You requested up to 900 tokens, "
            "but can only afford 766."
        )
        self.assertEqual(_extract_affordable_token_limit(error), 766)


class AIViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ai-user",
            email="ai@example.com",
            password="StrongPass123!",
        )

    def test_index_redirects_when_logged_out(self):
        response = self.client.get("/app/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_index_page_loads(self):
        self.client.force_login(self.user)
        response = self.client.get("/app/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cow Calving Assistant")
        self.assertContains(response, "Quick prompts")
        self.assertContains(response, 'id="quick-prompts-panel"', html=False)
        self.assertContains(response, "accounts/feedback.js")
        self.assertContains(response, 'data-ai-endpoint="/app/ai/test/"')

    def test_index_supports_embedded_mode(self):
        self.client.force_login(self.user)
        response = self.client.get("/app/?embedded=1")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cow Calving Assistant")
        self.assertContains(response, "Show prompts")
        self.assertContains(response, "Ready for your question.")
        self.assertContains(response, 'data-quick-prompts-toggle', html=False)
        self.assertContains(response, 'class="chat-shell embedded-shell h-full rounded-none border-0 shadow-none overflow-hidden"', html=False)
        self.assertEqual(response.headers.get("X-Frame-Options"), "SAMEORIGIN")

    def test_ai_test_redirects_when_logged_out(self):
        response = self.client.get("/app/ai/test/?q=Check+cow")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_ai_test_requires_question(self):
        self.client.force_login(self.user)
        response = self.client.get("/app/ai/test/")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["ok"], False)

    @patch("cow_calving_ai.views.get_ai_advice")
    def test_ai_test_returns_advice(self, mocked_get_ai_advice):
        self.client.force_login(self.user)
        mocked_get_ai_advice.return_value = "Mocked AI advice"

        response = self.client.get("/app/ai/test/?q=Check+cow&cow_id=COW-009")
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload["ok"], True)
        self.assertEqual(payload["question"], "Check cow")
        self.assertEqual(payload["cow_id"], "COW-009")
        self.assertEqual(payload["advice"], "Mocked AI advice")
        self.assertIn("provider", payload)

