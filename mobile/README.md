# BasedDoor Mobile

Portable Android app for street encounters, traffic stops, and any
in-person situation where your home system isn't present.

---

## Requirements

- Python 3.11+
- [Buildozer](https://buildozer.readthedocs.io/) for APK compilation
- Android device with USB debugging enabled (for sideload)

---

## Quick Start (Dev / Desktop)

```bash
cd mobile/
pip install kivy httpx pygame plyer openWakeWord pyaudio

# Generate offline audio (requires Piper installed)
bash ../scripts/generate_mobile_audio.sh

# Run on desktop
python main.py
```

---

## Build APK (Android)

```bash
pip install buildozer

# Initialise buildozer (first time only)
buildozer init

# Edit buildozer.spec:
#   title = BasedDoor
#   package.name = baseddoor
#   package.domain = ca.stackbleed
#   requirements = python3,kivy,httpx,pygame,plyer

# Build debug APK
buildozer android debug

# Sideload to connected device
buildozer android deploy run
```

APK will be in `bin/baseddoor-*.apk` — share directly without the Play Store.

---

## Configuration

Edit `config.json` (auto-created on first run):

```json
{
  "ollama_endpoint":  "http://YOUR-HOME-IP:11434",
  "ollama_model":     "llama3.2:3b",
  "piper_endpoint":   "http://YOUR-HOME-IP:5000",
  "mode":             "polite_canadian",
  "offline_mode":     true,
  "hotword":          "Hey Door",
  "wireguard":        false
}
```

Set `wireguard: true` and configure WireGuard on your phone to reach your
home server from anywhere without exposing Ollama to the internet.

---

## Offline Mode

Offline mode plays pre-baked WAV responses instantly — no LLM, no network.
Recommended for high-stress situations where seconds matter.

Generate offline audio:
```bash
bash ../scripts/generate_mobile_audio.sh
```

This creates WAV files in `assets/responses/` using Piper TTS.

---

## Modes

| Mode | Response style |
|---|---|
| `polite_canadian` | Respectful, firm |
| `grok_based` | Short, direct |
| `maximum_refusal` | Full Charter citation |
| `user_clip` | Your own pre-recorded audio |

---

## Hotword

Default wake phrase: **"Hey Door"**

Uses [openWakeWord](https://github.com/dscripka/openWakeWord) — 100% local,
no cloud, no data sent anywhere.

Falls back to button press if openWakeWord is not installed.
