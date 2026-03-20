"""Tests — Vision Engine."""
from __future__ import annotations

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from custom_components.baseddoor.vision import VisionEngine
from custom_components.baseddoor.const import (
    VISION_DELIVERY,
    VISION_PLAIN,
    VISION_UNIFORMED,
    VISION_UNIDENTIFIED,
)


class TestVisionLabelNormalisation:
    """Unit tests for _normalise_label — no Ollama required."""

    @pytest.mark.parametrize("raw,expected", [
        ("uniformed_officer",   VISION_UNIFORMED),
        ("uniformed",           VISION_UNIFORMED),
        ("officer",             VISION_UNIFORMED),
        ("police",              VISION_UNIFORMED),
        ("plain_clothes",       VISION_PLAIN),
        ("plain",               VISION_PLAIN),
        ("official",            VISION_PLAIN),
        ("delivery_person",     VISION_DELIVERY),
        ("delivery",            VISION_DELIVERY),
        ("courier",             VISION_DELIVERY),
        ("unidentified",        VISION_UNIDENTIFIED),
        ("unknown",             VISION_UNIDENTIFIED),
        ("UNIFORMED_OFFICER",   VISION_UNIFORMED),   # test lowercase normalisation
        ("  uniformed_officer", VISION_UNIFORMED),   # leading whitespace
        ("gibberish",           VISION_UNIDENTIFIED),
        ("",                    VISION_UNIDENTIFIED),
    ])
    def test_label_normalisation(self, raw, expected):
        result = VisionEngine._normalise_label(raw.strip().lower())
        assert result == expected, f"Input '{raw}' → expected {expected}, got {result}"

    def test_partial_match_in_sentence(self):
        """LLaVA sometimes returns a sentence instead of a bare label."""
        raw = "The image shows a uniformed officer standing at the door."
        result = VisionEngine._normalise_label(raw.lower())
        assert result == VISION_UNIFORMED

    def test_delivery_in_context(self):
        raw = "This appears to be a delivery person with a large parcel."
        result = VisionEngine._normalise_label(raw.lower())
        assert result == VISION_DELIVERY


class TestVisionEngineConnection:
    """Test that VisionEngine returns UNIDENTIFIED gracefully when Ollama is down."""

    @pytest.mark.asyncio
    async def test_returns_unidentified_on_timeout(self):
        engine = VisionEngine("http://localhost:19999", "llava:7b")
        fake_image = b"\xff\xd8\xff" + b"\x00" * 50
        result = await engine.classify_visitor(fake_image)
        assert result == VISION_UNIDENTIFIED

    @pytest.mark.asyncio
    async def test_returns_unidentified_on_empty_image(self):
        engine = VisionEngine("http://localhost:19999", "llava:7b")
        result = await engine.classify_visitor(b"")
        assert result == VISION_UNIDENTIFIED
