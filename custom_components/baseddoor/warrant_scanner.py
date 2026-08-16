"""Legal-document extraction helper for BasedDoor.

Despite the historical class name, this module does NOT validate warrants.
It extracts visible fields and identifies OCR/readability concerns for human review.
"""
from __future__ import annotations

import base64
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import httpx

_LOGGER = logging.getLogger(__name__)
OCR_TIMEOUT = 45.0
LLM_TIMEOUT = 30.0


@dataclass
class WarrantData:
    document_type: str = "unknown"
    issuing_person: str = ""
    issuing_court: str = ""
    date_issued: str = ""
    date_expires: str = ""
    target_address: str = ""
    scope_text: str = ""
    executing_officer: str = ""
    badge_number: str = ""
    signature_visible: bool = False
    seal_visible: bool = False
    raw_ocr_text: str = ""
    extraction_confidence: str = "low"
    raw_json: dict = field(default_factory=dict)


@dataclass
class WarrantCheckResult:
    # Backward-compatible attribute names; semantics changed deliberately.
    summary: str = ""
    red_flags: list[str] = field(default_factory=list)   # review flags, not invalidity
    green_flags: list[str] = field(default_factory=list) # observed fields, not validity
    overall_status: str = "unreadable"                  # readable/needs_review/unreadable
    spoken_summary: str = ""
    disclaimer: str = (
        "Automated image and text extraction only. BasedDoor has not determined "
        "the document's authenticity, legal validity, scope, or the visitor's authority. "
        "Review the original document and obtain qualified legal advice where appropriate."
    )


EXTRACTION_PROMPT = """
Extract only what is visibly readable in this legal document image.
Do not infer missing text and do not determine whether the document is legally valid.
Return ONLY JSON with:
{
  "document_type": "visible title/type or unknown",
  "issuing_person": "printed name or empty",
  "issuing_court": "printed court or empty",
  "date_issued": "printed date or empty",
  "date_expires": "printed expiry date or empty",
  "target_address": "printed address or empty",
  "scope_text": "visible scope/items text or empty",
  "executing_officer": "printed officer name or empty",
  "badge_number": "printed number or empty",
  "signature_visible": true,
  "seal_visible": false,
  "raw_ocr_text": "all readable text",
  "extraction_confidence": "low|medium|high"
}
If uncertain, leave the field empty and lower confidence.
""".strip()

REVIEW_PROMPT = """
You are reviewing OCR output from a Canadian legal document for READABILITY and
FIELD COMPLETENESS only. You are not determining authenticity or legal validity.
Do not say valid, invalid, lawful, unlawful, enforceable, or unenforceable.

Return ONLY JSON:
{
  "overall_status": "readable|needs_review|unreadable",
  "review_flags": ["missing/unreadable/ambiguous fields requiring human review"],
  "observed_fields": ["fields clearly extracted"],
  "summary": "plain-language extraction summary; no legal conclusion",
  "spoken_summary": "one calm sentence under 25 words saying extraction completed and human review is required"
}
""".strip()


class WarrantScanner:
    def __init__(self, ollama_endpoint: str, llava_model: str, llm_model: str) -> None:
        self._endpoint = ollama_endpoint.rstrip("/")
        self._llava = llava_model
        self._llm = llm_model

    async def scan(self, image_bytes: bytes) -> WarrantCheckResult:
        data = await self._extract_fields(image_bytes)
        return await self._review_extraction(data)

    async def _extract_fields(self, image_bytes: bytes) -> WarrantData:
        payload = {
            "model": self._llava,
            "prompt": EXTRACTION_PROMPT,
            "images": [base64.b64encode(image_bytes).decode()],
            "stream": False,
            "options": {"temperature": 0.0, "num_predict": 700},
        }
        try:
            async with httpx.AsyncClient(timeout=OCR_TIMEOUT) as client:
                resp = await client.post(f"{self._endpoint}/api/generate", json=payload)
                resp.raise_for_status()
                parsed = self._parse_json_response(resp.json().get("response", ""))
                if not parsed:
                    return WarrantData()
                return WarrantData(
                    document_type=str(parsed.get("document_type", "unknown")),
                    issuing_person=str(parsed.get("issuing_person", "")),
                    issuing_court=str(parsed.get("issuing_court", "")),
                    date_issued=str(parsed.get("date_issued", "")),
                    date_expires=str(parsed.get("date_expires", "")),
                    target_address=str(parsed.get("target_address", "")),
                    scope_text=str(parsed.get("scope_text", "")),
                    executing_officer=str(parsed.get("executing_officer", "")),
                    badge_number=str(parsed.get("badge_number", "")),
                    signature_visible=bool(parsed.get("signature_visible", False)),
                    seal_visible=bool(parsed.get("seal_visible", False)),
                    raw_ocr_text=str(parsed.get("raw_ocr_text", "")),
                    extraction_confidence=str(parsed.get("extraction_confidence", "low")),
                    raw_json=parsed,
                )
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("Document extraction failed: %s", exc)
            return WarrantData()

    async def _review_extraction(self, data: WarrantData) -> WarrantCheckResult:
        document = {
            "document_type": data.document_type,
            "issuing_person": data.issuing_person,
            "issuing_court": data.issuing_court,
            "date_issued": data.date_issued,
            "date_expires": data.date_expires,
            "target_address": data.target_address,
            "scope_text": data.scope_text,
            "executing_officer": data.executing_officer,
            "badge_number": data.badge_number,
            "signature_visible": data.signature_visible,
            "seal_visible": data.seal_visible,
            "extraction_confidence": data.extraction_confidence,
        }
        payload = {
            "model": self._llm,
            "system": REVIEW_PROMPT,
            "prompt": json.dumps(document, indent=2),
            "stream": False,
            "options": {"temperature": 0.0, "num_predict": 400},
        }
        try:
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
                resp = await client.post(f"{self._endpoint}/api/generate", json=payload)
                resp.raise_for_status()
                parsed = self._parse_json_response(resp.json().get("response", ""))
                if parsed:
                    status = parsed.get("overall_status", "needs_review")
                    if status not in {"readable", "needs_review", "unreadable"}:
                        status = "needs_review"
                    return WarrantCheckResult(
                        overall_status=status,
                        red_flags=list(parsed.get("review_flags", [])),
                        green_flags=list(parsed.get("observed_fields", [])),
                        summary=str(parsed.get("summary", "")),
                        spoken_summary=str(parsed.get(
                            "spoken_summary",
                            "Document extraction completed. Human review of the original document is required."
                        )),
                    )
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("Document extraction review failed: %s", exc)

        return WarrantCheckResult(
            overall_status="unreadable",
            red_flags=["Automated extraction could not reliably read the document"],
            summary="The image could not be extracted reliably. Review the original document directly.",
            spoken_summary="Document extraction was inconclusive. Please review the original document directly.",
        )

    @staticmethod
    def _parse_json_response(text: str) -> Optional[dict]:
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*", "", text).strip()
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end < start:
            return None
        try:
            obj = json.loads(text[start:end + 1])
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None
