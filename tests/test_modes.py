"""Tests — Response Modes and Escalation Logic."""
from __future__ import annotations

import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from custom_components.baseddoor.modes import (
    get_time_of_day,
    mode_label,
    should_escalate_mode,
)
from custom_components.baseddoor.const import (
    MODE_BASED,
    MODE_MAX,
    MODE_POLITE,
    MODE_CLIP,
)


class TestTimeOfDay:
    @pytest.mark.parametrize("hour,expected", [
        (5,  "morning"),
        (8,  "morning"),
        (11, "morning"),
        (12, "afternoon"),
        (15, "afternoon"),
        (16, "afternoon"),
        (17, "evening"),
        (20, "evening"),
        (21, "night"),
        (23, "night"),
        (0,  "night"),
        (4,  "night"),
    ])
    def test_time_buckets(self, hour, expected):
        # Patch datetime.now to return a fixed hour
        from datetime import datetime, timezone

        class FakeDateTime:
            @staticmethod
            def now(tz=None):
                class FakeTime:
                    pass
                t = FakeTime()
                t.hour = hour
                return t

        with patch("custom_components.baseddoor.modes.datetime", FakeDateTime):
            result = get_time_of_day()
        assert result == expected, f"Hour {hour} → expected {expected}, got {result}"


class TestModeLabel:
    def test_all_modes_have_labels(self):
        for mode in (MODE_POLITE, MODE_BASED, MODE_MAX, MODE_CLIP):
            label = mode_label(mode)
            assert isinstance(label, str)
            assert len(label) > 0

    def test_unknown_mode_returns_itself(self):
        result = mode_label("nonexistent_mode")
        assert result == "nonexistent_mode"

    def test_polite_label(self):
        assert "Polite" in mode_label(MODE_POLITE)

    def test_based_label(self):
        assert "Based" in mode_label(MODE_BASED) or "Grok" in mode_label(MODE_BASED)

    def test_max_label(self):
        assert "Max" in mode_label(MODE_MAX) or "Refusal" in mode_label(MODE_MAX)


class TestModeEscalation:
    def test_no_escalation_when_already_max(self):
        result = should_escalate_mode(MODE_MAX, knock_count=1, is_likely_leo=True)
        assert result == MODE_MAX

    def test_polite_escalates_to_based_on_officer(self):
        result = should_escalate_mode(MODE_POLITE, knock_count=1, is_likely_leo=True)
        assert result == MODE_BASED

    def test_polite_escalates_to_based_on_three_knocks(self):
        result = should_escalate_mode(MODE_POLITE, knock_count=3, is_likely_leo=False)
        assert result == MODE_BASED

    def test_polite_no_escalation_on_one_knock_no_officer(self):
        result = should_escalate_mode(MODE_POLITE, knock_count=1, is_likely_leo=False)
        assert result == MODE_POLITE

    def test_based_no_escalation_on_low_knock(self):
        result = should_escalate_mode(MODE_BASED, knock_count=1, is_likely_leo=False)
        assert result == MODE_BASED

    def test_night_officer_escalates_to_max(self):
        from datetime import datetime, timezone

        class FakeDateTime:
            @staticmethod
            def now(tz=None):
                class FakeTime:
                    hour = 23
                return FakeTime()

        with patch("custom_components.baseddoor.modes.datetime", FakeDateTime):
            result = should_escalate_mode(MODE_BASED, knock_count=1, is_likely_leo=True)
        assert result == MODE_MAX

    def test_night_no_officer_no_escalation_to_max(self):
        from datetime import datetime, timezone

        class FakeDateTime:
            @staticmethod
            def now(tz=None):
                class FakeTime:
                    hour = 23
                return FakeTime()

        with patch("custom_components.baseddoor.modes.datetime", FakeDateTime):
            result = should_escalate_mode(MODE_POLITE, knock_count=1, is_likely_leo=False)
        # Without officer at night, should not jump to MAX from POLITE
        assert result != MODE_MAX

    def test_clip_mode_never_escalated(self):
        # User clip mode should be preserved — it's an explicit user choice
        result = should_escalate_mode(MODE_CLIP, knock_count=5, is_likely_leo=True)
        # Clip mode has no escalation path defined — should return unchanged
        assert result == MODE_CLIP
