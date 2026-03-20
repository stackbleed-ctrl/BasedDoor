# BasedDoor — Hardware Guide

Everything you need to run BasedDoor with zero cloud dependency.

---

## 🏆 Recommended Doorbell Cameras (Local RTSP)

| Camera | Price (CAD) | RTSP | PoE | HA Integration | Notes |
|---|---|---|---|---|---|
| **Reolink Video Doorbell PoE** | ~$70 | ✅ Native | ✅ | Reolink integration | Best pick overall. Wired = reliable. |
| **Aqara G4 Doorbell** | ~$90 | ✅ | ❌ WiFi | Aqara Hub / HomeKit | Good image quality. Needs hub. |
| **Amcrest AD410** | ~$80 | ✅ | ✅ | Generic Camera (ONVIF) | Solid. ONVIF compliant. |
| Any ONVIF/RTSP cam | Varies | ✅ | Varies | Generic Camera | Any will work with BasedDoor. |

For warrant scanning, **higher resolution is better** — 1080p minimum, 4MP+ recommended.
The camera needs to clearly read printed text at arm's length distance.

### RTSP Stream URL Formats

**Reolink:**
```
rtsp://admin:PASSWORD@CAMERA-IP:554/h264Preview_01_main
```

**Amcrest:**
```
rtsp://admin:PASSWORD@CAMERA-IP:554/cam/realmonitor?channel=1&subtype=0
```

**Generic ONVIF:**
Use the [ONVIF Device Manager](https://sourceforge.net/projects/onvifdm/) to find your URL.

### Adding to Home Assistant

Settings → Devices & Services → Add Integration → **Generic Camera**

Enter your RTSP URL. Enable "Still image" for snapshot support (required for warrant scan).

---

## 🖥️ AI Server Hardware

BasedDoor's LLM and vision models run locally. Requirements depend on models used.

### Minimum (LLM only, no vision)

| Component | Spec |
|---|---|
| CPU | 4-core modern (Intel N100, AMD Ryzen 5) |
| RAM | 8GB |
| Storage | 20GB free |
| OS | Ubuntu 22.04+ / Debian 12 / HA OS with Ollama add-on |

**Model:** `llama3.2:3b` — runs entirely in RAM, ~2GB, fast on CPU.

### Recommended (LLM + LLaVA vision + warrant scan)

| Component | Spec |
|---|---|
| CPU | 8-core modern |
| RAM | 16GB |
| GPU | Optional — NVIDIA 8GB VRAM (speeds LLaVA significantly) |
| Storage | 50GB free |

**Models:** `llama3.2:3b` (2GB) + `llava:7b` (4.7GB)

### Great Hardware Picks (2026)

| Device | Price (CAD) | Notes |
|---|---|---|
| **Beelink EQ12 Mini PC** | ~$180 | Intel N100, 16GB RAM. Silent. Runs both models. |
| **Minisforum UM690** | ~$350 | Ryzen 9 6900HX. Handles LLaVA fast without GPU. |
| **Raspberry Pi 5 (8GB)** | ~$120 | Runs llama3.2:3b fine. LLaVA is slow (~30s). |
| Existing PC/server | — | If you have 16GB+ RAM spare, just use it. |
| HA Yellow / Green | ~$100 | Only for LLM. Too slow for LLaVA. |

---

## 🔊 Speakers

BasedDoor needs a speaker entity in Home Assistant to deliver responses.

| Option | Setup |
|---|---|
| **Google Nest / Amazon Echo** | Already in HA — but cloud-dependent. Not ideal. |
| **Sonos** | Local control available via HA Sonos integration. Good pick. |
| **Cheap Bluetooth speaker + HA Bluetooth** | Works. Reliability varies. |
| **PoE doorbell with built-in speaker** (Reolink) | Best option — no extra device. |
| **Raspberry Pi + speaker + HA media player** | DIY but fully local. |

For the front door, use the **Reolink's built-in speaker** — zero extra hardware,
and the audio comes directly from the doorbell unit in the officer's face.

---

## 🎤 Microphone (for Whisper STT)

Optional — used to transcribe visitor speech.

| Option | Notes |
|---|---|
| Reolink doorbell built-in mic | Works via HA audio entity |
| USB mic on HA server | Requires HA audio input entity |
| VoIP doorbell | Best audio quality |

---

## 🔔 Ring Doorbell

See `docs/RING_NOTES.md`. Short version: it works, but it sends your door
footage to Amazon. For a Charter rights tool, that's not ideal.
The Reolink PoE costs the same and is fully local.

---

## 📶 Network Recommendations

- Run your AI server and cameras on a **dedicated IoT VLAN**
- Block all IoT VLAN traffic from reaching the internet (cameras especially)
- HA server on main LAN with access to IoT VLAN for camera streams
- WireGuard for remote access to BasedDoor Mobile
- No ports exposed to the internet — VPN only
