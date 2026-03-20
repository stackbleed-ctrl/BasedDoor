"""
BasedDoor — Warrant Scanner
Captures a camera snapshot of a document held to the door, runs OCR extraction
via LLaVA (vision LLM) + optional Tesseract, then passes structured data to
the LLM for a basic sanity check against Canadian warrant requirements.

This is a document HELPER — not a legal validator. Output always includes a
disclaimer and recommendation to consult counsel.

Canadian statutory reference:
  - Search warrants: Criminal Code s.487
  - Telewarrants:    Criminal Code s.487.1
  - Production orders: Criminal Code s.487.012
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import httpx

_LOGGER = logging.getLogger(__name__)

OCR_TIMEOUT  = 45.0
LLM_TIMEOUT  = 30.0

# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class WarrantData:
    """Structured fields extracted from the document image."""
    document_type:    str = "unknown"          # e.g. "search warrant", "arrest warrant"
    issuing_judge:    str = ""
    issuing_court:    str = ""
    date_issued:      str = ""
    date_expires:     str = ""
    target_address:   str = ""
    items_to_seize:   str = ""
    executing_officer: str = ""
    badge_number:     str = ""
    signature_present: bool = False
    court_seal_present: bool = False
    raw_ocr_text:     str = ""
    extraction_confidence: str = "low"         # low / medium / high
    raw_json: dict = field(default_factory=dict)


@dataclass
class WarrantCheckResult:
    """Output of the LLM sanity check."""
    summary:          str = ""
    red_flags:        list[str] = field(default_factory=list)
    green_flags:      list[str] = field(default_factory=list)
    overall_status:   str = "unknown"          # appears_valid / red_flags_present / unreadable
    spoken_summary:   str = ""                 # short TTS-ready version
    disclaimer:       str = (
        "This is an automated extraction only — not legal validation. "
        "Do not make compliance decisions without reviewing the original "
        "document with qualified legal counsel."
    )


# ── LLaVA extraction prompt ───────────────────────────────────────────────────

EXTRACTION_PROMPT = """
You are a document extraction assistant. A warrant or legal document is being
held up to a security camera. Extract the following fields from the image and
return ONLY a valid JSON object — no preamble, no explanation, no markdown.

Required JSON keys:
{
  "document_type":       "search warrant | arrest warrant | production order | other | unknown",
  "issuing_judge":       "full name or empty string",
  "issuing_court":       "court name or empty string",
  "date_issued":         "YYYY-MM-DD or empty string",
  "date_expires":        "YYYY-MM-DD or empty string",
  "target_address":      "full address or empty string",
  "items_to_seize":      "brief description or empty string",
  "executing_officer":   "name or empty string",
  "badge_number":        "badge/regimental number or empty string",
  "signature_present":   true or false,
  "court_seal_present":  true or false,
  "raw_ocr_text":        "all readable text from the document",
  "extraction_confidence": "low | medium | high"
}

If the image is too blurry or dark to read, set extraction_confidence to "low"
and populate raw_ocr_text with whatever is visible.
Return ONLY the JSON object.
""".strip()


# ── LLM sanity check prompt ───────────────────────────────────────────────────

SANITY_CHECK_SYSTEM = """
You are Warrant Checker, a Canadian legal document sanity check assistant.
You are NOT a lawyer and do NOT provide legal advice.
Your job is to review extracted warrant data and flag obvious issues under
Canadian law — specifically Criminal Code s.487 for search warrants.

A valid Canadian search warrant must typically include:
  1. Named issuing judge (justice of the peace or superior court judge)
  2. Named issuing court
  3. Issuance date
  4. Specific address of premises to be searched
  5. Specific items or categories of items to be seized
  6. Authorising officer / named informant
  7. Judge's signature
  8. Court seal (recommended, not always strictly required)

Flag as RED FLAGS any of the following:
  - Missing judge name
  - Missing court name
  - Missing or expired date
  - Overly broad scope (e.g. "all items", "anything relevant")
  - Missing target address or mismatched address
  - No signature present
  - Document type is not a warrant (e.g. summons, notice)
  - Extraction confidence is low (document may be unreadable)

Output ONLY a valid JSON object:
{
  "overall_status": "appears_valid | red_flags_present | unreadable",
  "red_flags": ["list of issues found"],
  "green_flags": ["list of elements that appear correct"],
  "summary": "2-3 sentence plain-English summary",
  "spoken_summary": "1 sentence, TTS-ready, calm and factual, under 25 words"
}
""".strip()


# ── Main scanner class ────────────────────────────────────────────────────────

class WarrantScanner:
    """
    Full pipeline:
      camera snapshot → LLaVA OCR extraction → JSON parse → LLM sanity check → result
    """

    def __init__(self, ollama_endpoint: str, llava_model: str, llm_model: str) -> None:
        self._endpoint  = ollama_endpoint.rstrip("/")
        self._llava     = llava_model
        self._llm       = llm_model

    async def scan(self, image_bytes: bytes) -> WarrantCheckResult:
        """
        Full scan pipeline. Returns a WarrantCheckResult.
        Never raises — all errors produce a safe fallback result.
        """
        _LOGGER.info("BasedDoor Warrant: starting scan (%d bytes)", len(image_bytes))

        # Step 1: Extract fields via LLaVA
        warrant_data = await self._extract_fields(image_bytes)

        # Step 2: Sanity check via LLM
        result = await self._sanity_check(warrant_data)

        _LOGGER.info(
            "BasedDoor Warrant: scan complete — status='%s', red_flags=%d",
            result.overall_status,
            len(result.red_flags),
        )
        return result

    async def _extract_fields(self, image_bytes: bytes) -> WarrantData:
        """Use LLaVA to OCR and extract structured fields from the document image."""
        import base64

        b64 = base64.b64encode(image_bytes).decode()
        payload = {
            "model": self._llava,
            "system": "You are a document OCR extraction assistant. Return only valid JSON.",
            "prompt": EXTRACTION_PROMPT,
            "images": [b64],
            "stream": False,
            "options": {"temperature": 0.05, "num_predict": 600},
        }

        try:
            async with httpx.AsyncClient(timeout=OCR_TIMEOUT) as client:
                resp = await client.post(f"{self._endpoint}/api/generate", json=payload)
                resp.raise_for_status()
                raw_text = resp.json().get("response", "").strip()
                _LOGGER.debug("BasedDoor Warrant OCR raw: %s", raw_text[:200])

                parsed = self._parse_json_response(raw_text)
                if not parsed:
                    _LOGGER.warning("BasedDoor Warrant: LLaVA JSON parse failed")
                    return WarrantData(
                        raw_ocr_text=raw_text,
                        extraction_confidence="low",
                    )

                return WarrantData(
                    document_type=parsed.get("document_type", "unknown"),
                    issuing_judge=parsed.get("issuing_judge", ""),
                    issuing_court=parsed.get("issuing_court", ""),
                    date_issued=parsed.get("date_issued", ""),
                    date_expires=parsed.get("date_expires", ""),
                    target_address=parsed.get("target_address", ""),
                    items_to_seize=parsed.get("items_to_seize", ""),
                    executing_officer=parsed.get("executing_officer", ""),
                    badge_number=parsed.get("badge_number", ""),
                    signature_present=bool(parsed.get("signature_present", False)),
                    court_seal_present=bool(parsed.get("court_seal_present", False)),
                    raw_ocr_text=parsed.get("raw_ocr_text", ""),
                    extraction_confidence=parsed.get("extraction_confidence", "low"),
                    raw_json=parsed,
                )

        except httpx.TimeoutException:
            _LOGGER.error("BasedDoor Warrant: LLaVA OCR timed out")
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("BasedDoor Warrant: OCR error: %s", exc)

        return WarrantData(extraction_confidence="low")

    async def _sanity_check(self, data: WarrantData) -> WarrantCheckResult:
        """Pass extracted data to LLM for structured sanity check."""
        user_msg = json.dumps({
            "document_type":        data.document_type,
            "issuing_judge":        data.issuing_judge,
            "issuing_court":        data.issuing_court,
            "date_issued":          data.date_issued,
            "date_expires":         data.date_expires,
            "target_address":       data.target_address,
            "items_to_seize":       data.items_to_seize,
            "signature_present":    data.signature_present,
            "court_seal_present":   data.court_seal_present,
            "extraction_confidence": data.extraction_confidence,
        }, indent=2)

        payload = {
            "model": self._llm,
            "system": SANITY_CHECK_SYSTEM,
            "prompt": f"Analyse this warrant data:\n{user_msg}\n\nReturn only the JSON result.",
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 400},
        }

        try:
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
                resp = await client.post(f"{self._endpoint}/api/generate", json=payload)
                resp.raise_for_status()
                raw_text = resp.json().get("response", "").strip()
                parsed = self._parse_json_response(raw_text)

                if parsed:
                    result = WarrantCheckResult(
                        overall_status=parsed.get("overall_status", "unknown"),
                        red_flags=parsed.get("red_flags", []),
                        green_flags=parsed.get("green_flags", []),
                        summary=parsed.get("summary", ""),
                        spoken_summary=parsed.get("spoken_summary", ""),
                    )
                    # Ensure spoken_summary always exists
                    if not result.spoken_summary:
                        result.spoken_summary = self._build_spoken_summary(result, data)
                    return result

        except httpx.TimeoutException:
            _LOGGER.error("BasedDoor Warrant: LLM sanity check timed out")
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("BasedDoor Warrant: sanity check error: %s", exc)

        # Fallback: unreadable result
        return self._unreadable_result(data)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_json_response(text: str) -> Optional[dict]:
        """Extract and parse JSON from LLM output, tolerating markdown fences."""
        # Strip markdown fences
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*",     "", text)
        text = text.strip()

        # Find first { ... } block
        start = text.find("{")
        end   = text.rfind("}")
        if start == -1 or end == -1:
            return None
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _build_spoken_summary(result: WarrantCheckResult, data: WarrantData) -> str:
        """Build a TTS-ready one-liner fallback."""
        if result.overall_status == "unreadable":
            return (
                "Document scan was inconclusive. Image may be too blurry. "
                "Do not comply without reviewing the original with legal counsel."
            )
        judge = data.issuing_judge or "unknown judge"
        date  = data.date_issued  or "unknown date"
        flags = len(result.red_flags)
        if flags == 0:
            return (
                f"Warrant appears to be issued by {judge} on {date}. "
                "No immediate red flags detected. Recommend full legal review before complying."
            )
        return (
            f"Warrant scan found {flags} potential issue{'s' if flags > 1 else ''}. "
            "Recommend immediate legal consultation before taking any action."
        )

    @staticmethod
    def _unreadable_result(data: WarrantData) -> WarrantCheckResult:
        return WarrantCheckResult(
            overall_status="unreadable",
            red_flags=["Document could not be read clearly — image may be blurry or too dark"],
            green_flags=[],
            summary=(
                "The document scan was inconclusive. The image quality was insufficient "
                "for reliable extraction. Ask the officer to hold the document closer and "
                "steadier to the camera, or request a second attempt."
            ),
            spoken_summary=(
                "Warrant scan inconclusive. Image unclear. "
                "Do not comply without reviewing the original with legal counsel."
            ),
        )
