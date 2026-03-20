"""Tests — Encrypted Logger."""
from __future__ import annotations

import json
import os
import tempfile

import pytest
from cryptography.fernet import Fernet

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from custom_components.baseddoor.logger import InteractionLogger


@pytest.fixture
def tmp_log_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def fernet_key():
    return Fernet.generate_key().decode()


class TestEncryptedLogger:
    def test_plaintext_log_written(self, tmp_log_dir):
        logger = InteractionLogger(tmp_log_dir, encrypt=False)
        ts = logger.log_interaction(
            mode="polite_canadian",
            vision_result="unidentified",
            visitor_speech="hello",
            response_text="No consent.",
            knock_count=1,
            trigger_source="test",
        )
        files = os.listdir(tmp_log_dir)
        assert any("transcript" in f for f in files)
        assert any(ts in f for f in files)

    def test_plaintext_content_correct(self, tmp_log_dir):
        logger = InteractionLogger(tmp_log_dir, encrypt=False)
        ts = logger.log_interaction(
            mode="grok_based",
            vision_result="uniformed_officer",
            visitor_speech="police open up",
            response_text="No warrant. No consent.",
            knock_count=2,
            trigger_source="local_rtsp",
        )
        transcript_file = os.path.join(tmp_log_dir, f"{ts}_transcript.json")
        assert os.path.exists(transcript_file)
        with open(transcript_file) as f:
            data = json.load(f)
        assert data["mode"] == "grok_based"
        assert data["vision_result"] == "uniformed_officer"
        assert data["knock_count"] == 2
        assert "s.7" in data["charter_sections"]
        assert "s.8" in data["charter_sections"]

    def test_encrypted_file_is_not_plaintext(self, tmp_log_dir, fernet_key):
        logger = InteractionLogger(tmp_log_dir, encrypt=True, key=fernet_key)
        ts = logger.log_interaction(
            mode="maximum_refusal",
            vision_result="uniformed_officer",
            visitor_speech="",
            response_text="Section 7 and 8 invoked.",
            knock_count=1,
            trigger_source="test",
        )
        enc_file = os.path.join(tmp_log_dir, f"{ts}_transcript.json.enc")
        assert os.path.exists(enc_file), "Encrypted file not created"
        with open(enc_file, "rb") as f:
            raw = f.read()
        # Should NOT be readable as JSON directly
        with pytest.raises(Exception):
            json.loads(raw.decode("utf-8", errors="strict"))

    def test_encrypted_file_decrypts_correctly(self, tmp_log_dir, fernet_key):
        logger = InteractionLogger(tmp_log_dir, encrypt=True, key=fernet_key)
        ts = logger.log_interaction(
            mode="maximum_refusal",
            vision_result="unidentified",
            visitor_speech="show me your warrant",
            response_text="No consent.",
            knock_count=3,
            trigger_source="ring_doorbell",
        )
        enc_file = os.path.join(tmp_log_dir, f"{ts}_transcript.json.enc")
        fernet = Fernet(fernet_key.encode())
        with open(enc_file, "rb") as f:
            raw = f.read()
        decrypted = json.loads(fernet.decrypt(raw).decode())
        assert decrypted["visitor_speech"] == "show me your warrant"
        assert decrypted["knock_count"] == 3

    def test_snapshot_written_encrypted(self, tmp_log_dir, fernet_key):
        logger = InteractionLogger(tmp_log_dir, encrypt=True, key=fernet_key)
        fake_image = b"\xff\xd8\xff" + b"\x00" * 100  # fake JPEG bytes
        logger.log_snapshot("20260320_120000", fake_image)
        enc_file = os.path.join(tmp_log_dir, "20260320_120000_snapshot.jpg.enc")
        assert os.path.exists(enc_file)
        fernet = Fernet(fernet_key.encode())
        with open(enc_file, "rb") as f:
            decrypted = fernet.decrypt(f.read())
        assert decrypted == fake_image

    def test_list_interactions_returns_records(self, tmp_log_dir, fernet_key):
        logger = InteractionLogger(tmp_log_dir, encrypt=True, key=fernet_key)
        for i in range(3):
            logger.log_interaction(
                mode="polite_canadian",
                vision_result="unidentified",
                visitor_speech=f"visitor {i}",
                response_text="No consent.",
                knock_count=i + 1,
                trigger_source="test",
            )
        records = logger.list_interactions()
        assert len(records) == 3
        knock_counts = {r["knock_count"] for r in records}
        assert knock_counts == {1, 2, 3}

    def test_export_zip_created(self, tmp_log_dir, fernet_key):
        logger = InteractionLogger(tmp_log_dir, encrypt=True, key=fernet_key)
        logger.log_interaction(
            mode="grok_based",
            vision_result="unidentified",
            visitor_speech="",
            response_text="No.",
            knock_count=1,
            trigger_source="test",
        )
        import zipfile
        zip_path = os.path.join(tmp_log_dir, "export_test")
        result = logger.export_zip(zip_path)
        assert os.path.exists(result)
        with zipfile.ZipFile(result) as z:
            names = z.namelist()
        assert len(names) >= 1

    def test_bad_key_disables_encryption(self, tmp_log_dir):
        """Logger with invalid key should fall back to unencrypted."""
        logger = InteractionLogger(tmp_log_dir, encrypt=True, key="not-a-valid-fernet-key")
        assert logger._encrypt is False

    def test_no_key_no_encryption(self, tmp_log_dir):
        logger = InteractionLogger(tmp_log_dir, encrypt=True, key=None)
        assert logger._fernet is None
