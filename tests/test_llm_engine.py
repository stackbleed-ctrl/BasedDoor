"""Tests — LLM Engine and Prompt Builder."""
from __future__ import annotations

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from custom_components.baseddoor.llm_engine import (
    FALLBACKS,
    LLMContext,
    OllamaEngine,
    build_system_prompt,
    build_user_message,
)
from custom_components.baseddoor.const import (
    MODE_BASED,
    MODE_MAX,
    MODE_POLITE,
    VISION_UNIFORMED,
    VISION_UNIDENTIFIED,
)


class TestLLMContext:
    def test_is_likely_leo_vision(self):
        ctx = LLMContext(mode=MODE_POLITE, vision_result=VISION_UNIFORMED)
        assert ctx.is_likely_leo is True

    def test_is_likely_leo_speech(self):
        ctx = LLMContext(mode=MODE_POLITE, visitor_speech="RCMP officer at the door")
        assert ctx.is_likely_leo is True

    def test_is_likely_leo_false(self):
        ctx = LLMContext(mode=MODE_POLITE, vision_result=VISION_UNIDENTIFIED, visitor_speech="hello")
        assert ctx.is_likely_leo is False

    def test_has_claimed_emergency_true(self):
        ctx = LLMContext(mode=MODE_POLITE, visitor_speech="there's a fire next door")
        assert ctx.has_claimed_emergency is True

    def test_has_claimed_emergency_false(self):
        ctx = LLMContext(mode=MODE_POLITE, visitor_speech="I have a package")
        assert ctx.has_claimed_emergency is False

    def test_claims_warrant_true(self):
        ctx = LLMContext(mode=MODE_POLITE, visitor_speech="I have a search warrant")
        assert ctx.claims_warrant is True

    def test_claims_warrant_false(self):
        ctx = LLMContext(mode=MODE_POLITE, visitor_speech="just want to talk")
        assert ctx.claims_warrant is False


class TestPromptBuilder:
    def test_base_identity_present(self):
        ctx = LLMContext(mode=MODE_POLITE)
        prompt = build_system_prompt(ctx)
        assert "BasedDoor" in prompt
        assert "Charter" in prompt
        assert "never consent" in prompt.lower() or "never" in prompt.lower()

    def test_polite_mode_instruction(self):
        ctx = LLMContext(mode=MODE_POLITE)
        prompt = build_system_prompt(ctx)
        assert "Polite Canadian" in prompt

    def test_based_mode_instruction(self):
        ctx = LLMContext(mode=MODE_BASED)
        prompt = build_system_prompt(ctx)
        assert "Grok-Based" in prompt

    def test_max_mode_instruction(self):
        ctx = LLMContext(mode=MODE_MAX)
        prompt = build_system_prompt(ctx)
        assert "Maximum Refusal" in prompt

    def test_leo_addendum_injected_for_officer(self):
        ctx = LLMContext(mode=MODE_POLITE, vision_result=VISION_UNIFORMED)
        prompt = build_system_prompt(ctx)
        assert "law enforcement" in prompt.lower()
        assert "exigent" in prompt.lower()

    def test_leo_addendum_not_injected_for_unknown(self):
        ctx = LLMContext(mode=MODE_POLITE, vision_result=VISION_UNIDENTIFIED)
        prompt = build_system_prompt(ctx)
        assert "exigent" not in prompt.lower()

    def test_emergency_addendum_injected(self):
        ctx = LLMContext(mode=MODE_POLITE, visitor_speech="there's an emergency")
        prompt = build_system_prompt(ctx)
        assert "emergency" in prompt.lower()
        assert "9-1-1" in prompt or "911" in prompt

    def test_warrant_addendum_injected(self):
        ctx = LLMContext(mode=MODE_POLITE, visitor_speech="we have a warrant")
        prompt = build_system_prompt(ctx)
        assert "camera" in prompt.lower()
        assert "verbal" in prompt.lower()

    def test_repeat_knock_addendum_injected(self):
        ctx = LLMContext(mode=MODE_POLITE, knock_count=4)
        prompt = build_system_prompt(ctx)
        assert "4" in prompt

    def test_repeat_knock_not_injected_for_first(self):
        ctx = LLMContext(mode=MODE_POLITE, knock_count=1)
        prompt = build_system_prompt(ctx)
        assert "knock_count" not in prompt

    def test_user_message_contains_vision(self):
        ctx = LLMContext(mode=MODE_POLITE, vision_result=VISION_UNIFORMED)
        msg = build_user_message(ctx)
        assert "uniformed officer" in msg

    def test_user_message_contains_visitor_speech(self):
        ctx = LLMContext(mode=MODE_POLITE, visitor_speech="please open up")
        msg = build_user_message(ctx)
        assert "please open up" in msg

    def test_user_message_no_speech(self):
        ctx = LLMContext(mode=MODE_POLITE, visitor_speech="")
        msg = build_user_message(ctx)
        assert "none captured" in msg


class TestFallbacks:
    def test_all_modes_have_fallback(self):
        for mode in (MODE_POLITE, MODE_BASED, MODE_MAX):
            assert mode in FALLBACKS
            assert len(FALLBACKS[mode]) > 20

    def test_fallbacks_contain_charter_language(self):
        for mode, text in FALLBACKS.items():
            assert any(kw in text.lower() for kw in ["consent", "warrant", "recording", "charter"]), \
                f"Fallback for {mode} missing Charter language"

    def test_max_fallback_mentions_sections(self):
        assert "Section 7" in FALLBACKS[MODE_MAX]
        assert "Section 8" in FALLBACKS[MODE_MAX]


class TestOllamaEngineFallback:
    """Test that OllamaEngine falls back gracefully when Ollama is unreachable."""

    @pytest.mark.asyncio
    async def test_generate_returns_none_on_connection_error(self):
        engine = OllamaEngine("http://localhost:19999", "llama3.2:3b")
        result = await engine.generate("system", "prompt")
        assert result is None

    @pytest.mark.asyncio
    async def test_generate_response_returns_fallback_on_failure(self):
        engine = OllamaEngine("http://localhost:19999", "llama3.2:3b")
        ctx = LLMContext(mode=MODE_POLITE)
        result = await engine.generate_response(ctx)
        assert result == FALLBACKS[MODE_POLITE]

    @pytest.mark.asyncio
    async def test_generate_response_fallback_based(self):
        engine = OllamaEngine("http://localhost:19999", "llama3.2:3b")
        ctx = LLMContext(mode=MODE_BASED)
        result = await engine.generate_response(ctx)
        assert result == FALLBACKS[MODE_BASED]
