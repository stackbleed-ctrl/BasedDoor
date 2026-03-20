# 🍁 BasedDoor

> *"The AI sentinel that answers your door so you don't have to."*
> Local-only. No cloud. No OpenAI. No cooperation.

[![HACS Custom][hacs-badge]][hacs-link]
[![License: MIT][license-badge]][license-link]
[![HA Version][ha-badge]][ha-link]
[![Offline-First](https://img.shields.io/badge/cloud-zero-red?style=flat-square)]()
[![Tests](https://img.shields.io/github/actions/workflow/status/StackBleed/BasedDoor/hacs_validate.yml?label=CI&style=flat-square)]()

---

## What Is BasedDoor?

BasedDoor is a **privacy-first, local AI door sentinel** for Home Assistant.

When someone knocks — police, solicitors, anyone — BasedDoor:

1. **Detects** the event (doorbell, motion, knock sensor)
2. **Optionally scans** the camera feed with LLaVA for uniforms or badges
3. **Speaks a polite, Charter-compliant response** via your door speaker using Piper TTS
4. **If shown a warrant** — scans and extracts the document details, runs a sanity check, speaks a summary
5. **Logs** the encounter — encrypted video, audio, transcript, and warrant scan results — entirely on-device
6. **Notifies** you silently on your phone

Zero cloud. Zero telemetry. Zero cooperation beyond what the law requires.

Inspired by a real police knock-and-chat at a Nova Scotia doorstep over an X post.
Inspired by **your rights under the Canadian Charter of Rights and Freedoms, s.7 and s.8.**

---

## 🎯 Features

| Feature | Status |
|---|---|
| 🗣️ Auto-voice response via Piper TTS | ✅ |
| 🧠 Local LLM via Ollama (llama3.2:3b) | ✅ |
| 👁️ Optional LLaVA uniform/badge vision detection | ✅ |
| 📄 Warrant document scan (OCR + LLM sanity check) | ✅ |
| 🎙️ Whisper STT (transcribe visitor speech) | ✅ |
| 📼 Encrypted local video/audio/transcript logging | ✅ |
| 📱 HA mobile push notification (silent) | ✅ |
| 🔁 Four response modes | ✅ |
| 🚨 Auto-escalation (night + officer → max refusal) | ✅ |
| 📱 Standalone Android app (portable encounters) | 🔨 Beta |
| 🔔 Ring doorbell support (with caveats) | ⚠️ See Note |
| 📷 Reolink / RTSP local cam support | ✅ Recommended |

---

## 🎭 Response Modes

| Mode | Vibe | Example |
|---|---|---|
| **Polite Canadian** | Respectful, firm, Charter-grounded | *"Thank you for visiting. No emergency is apparent. No warrant has been presented. Recording is active. Have a safe day."* |
| **Grok-Based** | Direct, zero-nonsense | *"No warrant. No emergency. No consent. Recording active. Bye."* |
| **Maximum Refusal** | Full Charter recitation | *"No emergency confirmed. No warrant presented. Under Section 7 of the Canadian Charter, the resident has the right to remain silent. Under Section 8, no consent is given to search or enter. Recording in progress. Please vacate immediately."* |
| **User Clip** | Plays your own pre-recorded audio | *Your voice, your rules.* |

---

## 📄 Warrant Scanner

When an officer presents a warrant, trigger `baseddoor.scan_warrant`:

1. BasedDoor announces: *"Please hold the document steady to the camera."*
2. LLaVA extracts: judge name, court, date, address, items to seize, signature, seal
3. LLM checks against Criminal Code s.487 requirements
4. BasedDoor speaks the result: *"Warrant appears to be issued by Judge X on date Y. No immediate red flags detected. Recommend full legal review before complying."*
5. Full OCR result and image saved locally, encrypted

**This is a document helper, not legal validation. Always consult a lawyer.**

---

## ⚡ One-Click HACS Install

### Prerequisites
- Home Assistant 2024.1+
- [HACS](https://hacs.xyz) installed
- [Ollama](https://ollama.ai) running locally (same machine or network)
- [Piper TTS](https://github.com/rhasspy/piper) (script provided)
- A doorbell or RTSP camera integrated with HA

### Step 1 — Add Repo to HACS

HACS → **Custom Repositories** → Add:
```
https://github.com/StackBleed/BasedDoor
```
Category: **Integration**

### Step 2 — Install

HACS → Integrations → Search **BasedDoor** → Install → Restart HA

### Step 3 — Configure

Settings → Devices & Services → Add Integration → **BasedDoor**

Fill in:
- Ollama endpoint (default: `http://localhost:11434`)
- Camera entity
- Speaker entity
- Response mode
- Vision toggle (requires LLaVA model)

### Step 4 — Run Setup Scripts (first time only)

```bash
# Install Ollama + pull models
bash scripts/install_ollama.sh

# Install Piper TTS
bash scripts/install_piper.sh

# Install Whisper STT (optional)
bash scripts/install_whisper.sh

# Pre-bake mobile offline audio
bash scripts/generate_mobile_audio.sh
```

For LLaVA vision + warrant scanning:
```bash
INSTALL_VISION=true bash scripts/install_ollama.sh
```

---

## 📷 Camera Recommendation

**Recommended:** Reolink Video Doorbell PoE (~$70 CAD)
- Full local RTSP stream — no cloud, no account
- Built-in speaker for BasedDoor TTS
- 1080p+ for warrant document scanning
- PoE — wired reliability, no WiFi dropouts

See `docs/HARDWARE.md` for full hardware guide.

### ⚠️ Ring Doorbell Note

Ring requires an Amazon cloud account. Your footage transits Amazon's servers.
Amazon has complied with law enforcement data requests without user notification.

This is architecturally incompatible with BasedDoor's privacy model.

See `docs/RING_NOTES.md` for details. If you're building a Charter rights tool,
use a local camera.

---

## 🛡️ Legal Shield

**Section 7** — Right to silence and security of the person.
You are not required to speak to police who knock without a warrant.

**Section 8** — Right against unreasonable search or seizure.
Without a warrant or genuine exigent circumstances, police cannot enter your home
or demand you engage.

See `docs/CHEATSHEET.md` for the full plain-English reference and decision tree.

> ⚠️ **BasedDoor is not legal advice.** Consult a lawyer for your specific situation.

---

## 🧪 Tests

```bash
pip install pytest pytest-asyncio

# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=custom_components/baseddoor --cov-report=term-missing
```

See `tests/` for full test suite covering encryption, LLM engine, vision,
warrant scanner, coordinator pipeline, and config flow.

---

## 📱 Mobile App

See `mobile/README.md` for build and sideload instructions.

Android APK via Buildozer. Offline-first. Hotword: *"Hey Door"*.

---

## 📋 Roadmap

- [ ] iOS app (Flutter)
- [ ] LLaVA badge/uniform detection improvements
- [ ] French language support (Québec / Bill 96)
- [ ] Warrant address cross-reference (match against HA zone)
- [ ] Multi-door / multi-camera support

---

## 🤝 Contributing

PRs welcome. MIT licensed. Fork it, ship it, tell your privacy circle.

---

## 📄 License

MIT — see `LICENSE`.

---

*Built in Sydney, Nova Scotia.*
*Dedicated to everyone who knows their rights but needed a robot to say it for them.*

[hacs-badge]: https://img.shields.io/badge/HACS-Custom-orange?style=flat-square
[hacs-link]: https://hacs.xyz
[license-badge]: https://img.shields.io/badge/License-MIT-blue?style=flat-square
[license-link]: LICENSE
[ha-badge]: https://img.shields.io/badge/HA-2024.1%2B-blue?style=flat-square
[ha-link]: https://home-assistant.io
