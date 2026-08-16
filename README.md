# 🍁 BasedDoor

**A local-first doorstep assistant for Home Assistant and Android.**

BasedDoor is a free, MIT-licensed project designed to help residents automate a calm, privacy-preserving doorstep response, keep local event records, and optionally use local AI without requiring a cloud AI service.

> **Current status: Alpha 0.2 hardening.** Do not treat untested hardware or AI output as authoritative. See `docs/SAFETY.md` and `docs/COMPATIBILITY.md`.

## What it does

BasedDoor can combine Home Assistant triggers, camera snapshots, a compatible local speaker, notifications, encrypted local logs, and optional local Ollama models.

The architecture is capability-driven:

**trigger → optional snapshot → optional local analysis → deterministic/AI response → optional speaker → local log → optional notification**

If a capability is missing, BasedDoor is expected to degrade cleanly rather than pretend the capability exists.

## Privacy principles

- local-first operation
- no telemetry in the BasedDoor integration
- no required cloud AI
- deterministic offline response path
- encrypted local logging available
- no hidden cloud speech-recognition fallback
- original evidence kept conceptually separate from AI interpretation

## Important truthfulness rules

BasedDoor does **not** claim that recording is active merely because a camera exists. Recording status remains fail-closed until a real recording integration positively confirms it.

Computer-vision classifications are hints, not identity or authority verification.

Document scanning is OCR/extraction assistance only. It does not determine whether a warrant or other legal document is authentic, valid, enforceable, or applicable.

## Installation profiles

### Lite — no local AI required

Use Home Assistant triggers plus a compatible speaker and/or phone notification. Responses are deterministic and work without Ollama.

### Local AI

Enable a local Ollama text model for adaptive phrasing. If Ollama fails, BasedDoor falls back to deterministic output.

### Vision

Optionally add a local vision model for image classification/document extraction. Vision is never required for the basic response path.

## Home Assistant

Prerequisites depend on the capabilities you want:

- Home Assistant 2024.1+
- HACS for custom-repository installation
- optional camera entity
- optional compatible media-player entity
- optional Ollama
- optional Piper-compatible local TTS endpoint

Add this repository as a HACS custom integration, restart Home Assistant, then add **BasedDoor** under Settings → Devices & services.

## Android

`mobile/` contains the conservative Alpha 0.2 Android client.

The mobile baseline is **button-first**, deterministic, and does not claim to record. A committed `buildozer.spec` and `.github/workflows/android.yml` provide a repeatable APK build path.

The Android app can run without Ollama. A local-network or VPN Ollama endpoint may be configured as an optional enhancement.

## Hardware

BasedDoor does not promise blanket brand support. It consumes Home Assistant capabilities. See `docs/COMPATIBILITY.md` for the field-test matrix.

Reolink is a useful local camera option, but Home Assistant currently does not expose Reolink two-way audio/TTS, so spoken output requires a separately verified speaker path.

## Canadian legal boundary

BasedDoor communicates configured responses and helps preserve/extract information. It is not legal advice and does not determine police authority, emergency authority, or document validity.

Canadian law includes warrant processes and circumstances where some search powers may be exercised without a warrant. Never use BasedDoor as instructions to physically obstruct lawful action. See `docs/SAFETY.md` and current official Canadian law.

## Development

```bash
python -m pip install -r requirements-dev.txt
ruff check custom_components/baseddoor mobile tests --select E,F,W,I --ignore E501,E402
pytest -q
```

CI belongs under `.github/workflows/` and should be green before a release is labelled tested.

## License

MIT. Free to use, inspect, fork, improve, and redistribute subject to the license.

---

**Product thesis → engineering invariants → evidence-backed capability map.**

BasedDoor should only claim what the running system can prove.
