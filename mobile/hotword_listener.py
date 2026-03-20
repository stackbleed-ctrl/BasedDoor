"""
BasedDoor Mobile — Hotword Listener
Uses openWakeWord (local, no cloud) for always-on phrase detection.
Falls back to a simple energy-threshold + keyword match if openWakeWord
is not installed (useful for dev/testing without full ML stack).
"""
from __future__ import annotations

import logging
import time
from typing import Callable

_LOGGER = logging.getLogger(__name__)

try:
    import openwakeword
    from openwakeword.model import Model as OWWModel
    HAS_OWW = True
except ImportError:
    HAS_OWW = False
    _LOGGER.warning("openWakeWord not installed — using fallback listener")


class HotwordListener:
    """
    Listens for a hotword phrase and fires a callback.

    Priority:
      1. openWakeWord (local, no cloud)
      2. Simple VAD + SpeechRecognition fallback (dev mode)
    """

    def __init__(self, phrase: str, callback: Callable[[], None]) -> None:
        self._phrase = phrase.lower()
        self._callback = callback
        self._running = False

    def start(self) -> None:
        self._running = True
        if HAS_OWW:
            self._run_oww()
        else:
            self._run_fallback()

    def stop(self) -> None:
        self._running = False

    # ── openWakeWord ─────────────────────────────────────────────────────────

    def _run_oww(self) -> None:
        """openWakeWord continuous audio processing loop."""
        try:
            import pyaudio
            import numpy as np

            oww = OWWModel(
                wakeword_models=["hey_door"],   # custom model slot
                inference_framework="onnx",
            )

            pa = pyaudio.PyAudio()
            stream = pa.open(
                rate=16000,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=1280,
            )
            _LOGGER.info("BasedDoor Hotword: openWakeWord listening for '%s'", self._phrase)

            while self._running:
                audio_chunk = stream.read(1280, exception_on_overflow=False)
                audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
                predictions = oww.predict(audio_array)

                for model_name, score in predictions.items():
                    if score > 0.7:
                        _LOGGER.info("BasedDoor Hotword: detected '%s' (score=%.2f)", model_name, score)
                        self._callback()
                        time.sleep(2)  # debounce

            stream.stop_stream()
            stream.close()
            pa.terminate()

        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("BasedDoor Hotword (OWW): error: %s", exc)
            self._run_fallback()

    # ── Fallback: SpeechRecognition keyword match ────────────────────────────

    def _run_fallback(self) -> None:
        """
        Dev-mode fallback: uses SpeechRecognition + Google/Vosk STT
        to detect the hotword phrase. Not recommended for production —
        Google STT requires internet.
        """
        try:
            import speech_recognition as sr

            recogniser = sr.Recognizer()
            mic = sr.Microphone(sample_rate=16000)

            _LOGGER.info(
                "BasedDoor Hotword (fallback): listening for '%s'", self._phrase
            )

            with mic as source:
                recogniser.adjust_for_ambient_noise(source, duration=1)

            while self._running:
                try:
                    with mic as source:
                        audio = recogniser.listen(source, timeout=5, phrase_time_limit=4)
                    # Try Vosk (offline) first
                    try:
                        text = recogniser.recognize_vosk(audio).lower()
                    except Exception:
                        text = ""

                    if self._phrase in text:
                        _LOGGER.info("BasedDoor Hotword (fallback): detected '%s'", self._phrase)
                        self._callback()
                        time.sleep(2)

                except sr.WaitTimeoutError:
                    pass
                except sr.UnknownValueError:
                    pass
                except Exception as exc:  # noqa: BLE001
                    _LOGGER.warning("BasedDoor Hotword (fallback): listen error: %s", exc)
                    time.sleep(1)

        except ImportError:
            _LOGGER.error(
                "BasedDoor Hotword: neither openWakeWord nor SpeechRecognition "
                "is installed. Hotword detection disabled. Use ACTIVATE button."
            )
