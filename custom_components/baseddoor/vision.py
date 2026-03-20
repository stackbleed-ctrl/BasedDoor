"""BasedDoor — Vision Engine (LLaVA via Ollama)."""
from __future__ import annotations

import base64
import logging
from typing import Optional

import httpx

from .const import (
    VISION_DELIVERY,
    VISION_PLAIN,
    VISION_UNIDENTIFIED,
    VISION_UNIFORMED,
)

_LOGGER = logging.getLogger(__name__)

VISION_TIMEOUT = 45.0  # LLaVA 7b is slower than text models

VISION_SYSTEM_PROMPT = """
You are a security camera analysis assistant. Analyse the image and classify the visitor.
Respond with ONLY one of these exact labels — no explanation, no punctuation, nothing else:

  uniformed_officer   — person wearing a police or law enforcement uniform, visible badge,
                        hi-vis vest with police markings, or tactical gear
  plain_clothes       — person in civilian clothing who appears purposeful/official
                        (e.g. carrying a clipboard, wearing a lanyard, holding ID)
  delivery_person     — person carrying a parcel, wearing delivery company uniform/vest
  unidentified        — anyone else, or image too unclear to classify

Respond with exactly one label from the list above.
""".strip()


class VisionEngine:
    """LLaVA-based visitor classification via Ollama multimodal endpoint."""

    def __init__(self, endpoint: str, model: str) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._model = model

    async def classify_visitor(self, image_bytes: bytes) -> str:
        """
        Classify the visitor in image_bytes.
        Returns one of the VISION_* constants from const.py.
        Falls back to VISION_UNIDENTIFIED on any error.
        """
        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        payload = {
            "model": self._model,
            "system": VISION_SYSTEM_PROMPT,
            "prompt": "Classify the visitor in this image.",
            "images": [b64_image],
            "stream": False,
            "options": {
                "temperature": 0.1,   # near-deterministic for classification
                "num_predict": 10,    # label only, very short
            },
        }

        try:
            async with httpx.AsyncClient(timeout=VISION_TIMEOUT) as client:
                resp = await client.post(
                    f"{self._endpoint}/api/generate",
                    json=payload,
                )
                resp.raise_for_status()
                raw = resp.json().get("response", "").strip().lower()
                _LOGGER.debug("BasedDoor Vision: raw label='%s'", raw)
                return self._normalise_label(raw)

        except httpx.TimeoutException:
            _LOGGER.warning("BasedDoor Vision: LLaVA timed out — defaulting to unidentified")
        except httpx.HTTPStatusError as exc:
            _LOGGER.error("BasedDoor Vision: HTTP %s", exc.response.status_code)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("BasedDoor Vision: unexpected error: %s", exc)

        return VISION_UNIDENTIFIED

    @staticmethod
    def _normalise_label(raw: str) -> str:
        """Map raw LLaVA output back to a known constant."""
        mapping = {
            "uniformed_officer": VISION_UNIFORMED,
            "uniformed": VISION_UNIFORMED,
            "officer": VISION_UNIFORMED,
            "police": VISION_UNIFORMED,
            "plain_clothes": VISION_PLAIN,
            "plain": VISION_PLAIN,
            "official": VISION_PLAIN,
            "delivery_person": VISION_DELIVERY,
            "delivery": VISION_DELIVERY,
            "courier": VISION_DELIVERY,
            "unidentified": VISION_UNIDENTIFIED,
            "unknown": VISION_UNIDENTIFIED,
        }
        for key, value in mapping.items():
            if key in raw:
                return value
        return VISION_UNIDENTIFIED
