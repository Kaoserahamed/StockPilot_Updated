"""Tests for the optional Gemini polishing and end-to-end answer_question."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services import ai_service


class TestMaybePolishWithGemini:
    @patch.object(ai_service, "settings")
    def test_returns_draft_when_ai_disabled(self, mock_settings) -> None:
        mock_settings.ai_enabled = False
        assert ai_service.maybe_polish_with_gemini("q", "draft", {}) == "draft"

    @patch.object(ai_service, "settings")
    @patch("google.generativeai", create=True)
    def test_returns_draft_on_error(self, mock_genai, mock_settings) -> None:
        mock_settings.ai_enabled = True
        mock_settings.gemini_api_key = "key"
        mock_settings.gemini_model = "gemini-1.5-flash"
        mock_genai.configure.side_effect = Exception("network")
        assert ai_service.maybe_polish_with_gemini("q", "draft", {}) == "draft"


class TestAnswerQuestion:
    @patch.object(ai_service, "maybe_polish_with_gemini", return_value="polished")
    @patch.object(ai_service, "_business_snapshot")
    @patch.object(ai_service, "_rule_answer", return_value="draft answer")
    def test_answer_returns_polished_draft_and_snapshot(
        self, mock_draft, mock_snap, mock_polish
    ) -> None:
        mock_snap.return_value = {
            "preset": "month",
            "profit": {},
            "inventory": {},
            "top_products": [],
            "customers": [],
            "suppliers": [],
        }

        answer, snap = ai_service.answer_question(MagicMock(), 1, "what about inventory")

        assert answer == "polished"
        assert snap["preset"] == "month"
