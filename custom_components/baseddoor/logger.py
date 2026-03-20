"""BasedDoor — Encrypted Local Interaction Logger."""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

_LOGGER = logging.getLogger(__name__)


class InteractionLogger:
    """
    Logs each door interaction to an encrypted local directory.

    Each interaction produces three files:
      {timestamp}_transcript.json.enc  — metadata + visitor transcript + LLM response
      {timestamp}_snapshot.jpg.enc     — camera snapshot (if available)
      {timestamp}_audio.wav.enc        — visitor audio (if available)

    Encryption: Fernet (AES-128-CBC + HMAC-SHA256).
    Key is stored in HA config entry and never leaves the device.
    """

    DATE_FORMAT = "%Y%m%d_%H%M%S"

    def __init__(self, log_dir: str, encrypt: bool = True, key: Optional[str] = None) -> None:
        self._log_dir = log_dir
        self._encrypt = encrypt
        self._fernet = None

        if encrypt and key:
            try:
                from cryptography.fernet import Fernet
                self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
            except Exception as exc:  # noqa: BLE001
                _LOGGER.error("BasedDoor Logger: failed to initialise encryption: %s", exc)
                self._encrypt = False

        os.makedirs(log_dir, exist_ok=True)

    def _ts(self) -> str:
        return datetime.now(tz=timezone.utc).strftime(self.DATE_FORMAT)

    def _write(self, path: str, data: bytes) -> None:
        if self._encrypt and self._fernet:
            data = self._fernet.encrypt(data)
            path = path + ".enc"
        with open(path, "wb") as fh:
            fh.write(data)
        _LOGGER.debug("BasedDoor Logger: wrote %s (%d bytes)", os.path.basename(path), len(data))

    def log_interaction(
        self,
        *,
        mode: str,
        vision_result: str,
        visitor_speech: str,
        response_text: str,
        knock_count: int = 1,
        trigger_source: str = "unknown",
    ) -> str:
        """
        Write a transcript JSON for this interaction.
        Returns the timestamp string used as file prefix.
        """
        ts = self._ts()
        record = {
            "timestamp_utc": ts,
            "trigger_source": trigger_source,
            "mode": mode,
            "knock_count": knock_count,
            "vision_result": vision_result,
            "visitor_speech": visitor_speech,
            "response_text": response_text,
            "charter_sections": ["s.7", "s.8"],
        }
        path = os.path.join(self._log_dir, f"{ts}_transcript.json")
        self._write(path, json.dumps(record, indent=2).encode())
        return ts

    def log_snapshot(self, ts: str, image_bytes: bytes) -> None:
        """Save camera snapshot for the interaction identified by ts."""
        path = os.path.join(self._log_dir, f"{ts}_snapshot.jpg")
        self._write(path, image_bytes)

    def log_audio(self, ts: str, audio_bytes: bytes) -> None:
        """Save visitor audio for the interaction identified by ts."""
        path = os.path.join(self._log_dir, f"{ts}_audio.wav")
        self._write(path, audio_bytes)

    def list_interactions(self) -> list[dict]:
        """
        Return a summary list of logged interactions (transcript metadata only).
        Decrypts if key is available; otherwise returns filenames only.
        """
        results = []
        for fname in sorted(os.listdir(self._log_dir), reverse=True):
            if "transcript" not in fname:
                continue
            fpath = os.path.join(self._log_dir, fname)
            try:
                with open(fpath, "rb") as fh:
                    raw = fh.read()
                if self._encrypt and self._fernet and fname.endswith(".enc"):
                    raw = self._fernet.decrypt(raw)
                results.append(json.loads(raw.decode()))
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning("BasedDoor Logger: could not read %s: %s", fname, exc)
                results.append({"filename": fname, "error": str(exc)})
        return results

    def export_zip(self, dest_path: str) -> str:
        """
        Create a ZIP archive of all log files at dest_path.
        Returns the final path of the ZIP file.
        """
        import zipfile

        zip_path = dest_path if dest_path.endswith(".zip") else dest_path + ".zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname in os.listdir(self._log_dir):
                fpath = os.path.join(self._log_dir, fname)
                if os.path.isfile(fpath):
                    zf.write(fpath, arcname=fname)
        _LOGGER.info("BasedDoor Logger: exported logs to %s", zip_path)
        return zip_path
