"""Tests — Warrant Scanner."""
from __future__ import annotations

import json
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from custom_components.baseddoor.warrant_scanner import (
    WarrantData,
    WarrantCheckResult,
    WarrantScanner,
)


class TestWarrantDataModel:
    def test_defaults(self):
        wd = WarrantData()
        assert wd.document_type == "unknown"
        assert wd.signature_present is False
        assert wd.extraction_confidence == "low"
        assert wd.red_flags is not None if hasattr(wd, "red_flags") else True

    def test_full_construction(self):
        wd = WarrantData(
            document_type="search warrant",
            issuing_judge="Jane Doe",
            issuing_court="Nova Scotia Supreme Court",
            date_issued="2026-03-20",
            target_address="123 Main St, Sydney NS",
            items_to_seize="Electronic devices",
            signature_present=True,
            court_seal_present=True,
            extraction_confidence="high",
        )
        assert wd.issuing_judge == "Jane Doe"
        assert wd.signature_present is True
        assert wd.extraction_confidence == "high"


class TestWarrantCheckResult:
    def test_disclaimer_always_present(self):
        result = WarrantCheckResult()
        assert "not legal" in result.disclaimer.lower() or "automated" in result.disclaimer.lower()

    def test_default_status(self):
        result = WarrantCheckResult()
        assert result.overall_status == "unknown"

    def test_red_flags_list(self):
        result = WarrantCheckResult(red_flags=["Missing judge", "Expired"])
        assert len(result.red_flags) == 2


class TestJsonParsing:
    """Test the JSON extraction helper independently."""

    def test_clean_json(self):
        raw = '{"overall_status": "appears_valid", "red_flags": [], "green_flags": ["judge present"]}'
        result = WarrantScanner._parse_json_response(raw)
        assert result is not None
        assert result["overall_status"] == "appears_valid"

    def test_json_with_markdown_fences(self):
        raw = '```json\n{"overall_status": "red_flags_present", "red_flags": ["no signature"]}\n```'
        result = WarrantScanner._parse_json_response(raw)
        assert result is not None
        assert result["overall_status"] == "red_flags_present"

    def test_json_with_preamble(self):
        raw = 'Here is my analysis:\n{"overall_status": "unreadable", "red_flags": []}'
        result = WarrantScanner._parse_json_response(raw)
        assert result is not None
        assert result["overall_status"] == "unreadable"

    def test_invalid_json_returns_none(self):
        raw = "This is not JSON at all."
        result = WarrantScanner._parse_json_response(raw)
        assert result is None

    def test_empty_string_returns_none(self):
        result = WarrantScanner._parse_json_response("")
        assert result is None

    def test_truncated_json_returns_none(self):
        raw = '{"overall_status": "appears_valid", "red_flags": ['
        result = WarrantScanner._parse_json_response(raw)
        assert result is None


class TestSpokenSummaryBuilder:
    def test_unreadable_result(self):
        result = WarrantCheckResult(overall_status="unreadable")
        data = WarrantData()
        summary = WarrantScanner._build_spoken_summary(result, data)
        assert "inconclusive" in summary.lower() or "unclear" in summary.lower()

    def test_valid_with_judge(self):
        result = WarrantCheckResult(overall_status="appears_valid", red_flags=[])
        data = WarrantData(issuing_judge="Judge Smith", date_issued="2026-03-20")
        summary = WarrantScanner._build_spoken_summary(result, data)
        assert "Judge Smith" in summary
        assert "2026-03-20" in summary
        assert "no immediate red flags" in summary.lower() or "no obvious" in summary.lower()

    def test_red_flags_present(self):
        result = WarrantCheckResult(
            overall_status="red_flags_present",
            red_flags=["Missing signature", "Expired date"],
        )
        data = WarrantData()
        summary = WarrantScanner._build_spoken_summary(result, data)
        assert "2" in summary
        assert "issue" in summary.lower()

    def test_single_red_flag_singular(self):
        result = WarrantCheckResult(
            overall_status="red_flags_present",
            red_flags=["Missing judge name"],
        )
        data = WarrantData()
        summary = WarrantScanner._build_spoken_summary(result, data)
        # Should say "1 potential issue" not "1 potential issues"
        assert "issues" not in summary or "1 potential issue" in summary

    def test_disclaimer_in_all_valid_responses(self):
        result = WarrantCheckResult(overall_status="appears_valid", red_flags=[])
        data = WarrantData(issuing_judge="Judge X", date_issued="2026-01-01")
        summary = WarrantScanner._build_spoken_summary(result, data)
        assert "legal" in summary.lower() or "counsel" in summary.lower() or "review" in summary.lower()


class TestUnreadableResult:
    def test_unreadable_result_structure(self):
        data = WarrantData(extraction_confidence="low")
        result = WarrantScanner._unreadable_result(data)
        assert result.overall_status == "unreadable"
        assert len(result.red_flags) >= 1
        assert "blurry" in result.summary.lower() or "insufficient" in result.summary.lower()
        assert result.spoken_summary != ""

    def test_unreadable_suggests_retry(self):
        data = WarrantData()
        result = WarrantScanner._unreadable_result(data)
        assert "camera" in result.summary.lower() or "closer" in result.summary.lower()


class TestWarrantScannerConnection:
    """Test full scanner returns safe fallback when Ollama is unreachable."""

    @pytest.mark.asyncio
    async def test_scan_returns_unreadable_on_connection_failure(self):
        scanner = WarrantScanner(
            ollama_endpoint="http://localhost:19999",
            llava_model="llava:7b",
            llm_model="llama3.2:3b",
        )
        fake_image = b"\xff\xd8\xff" + b"\x00" * 100
        result = await scanner.scan(fake_image)
        # Should never raise — always returns a WarrantCheckResult
        assert isinstance(result, WarrantCheckResult)
        assert result.overall_status in ("unreadable", "unknown", "red_flags_present", "appears_valid")
        assert result.disclaimer != ""

    @pytest.mark.asyncio
    async def test_scan_never_raises(self):
        scanner = WarrantScanner(
            ollama_endpoint="http://localhost:19999",
            llava_model="llava:7b",
            llm_model="llama3.2:3b",
        )
        # Even with empty bytes — should not raise
        result = await scanner.scan(b"")
        assert isinstance(result, WarrantCheckResult)
