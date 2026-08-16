# Compatibility model

BasedDoor supports **capabilities**, not brands.

A hardware SKU is considered supported only after its required capabilities have been tested.

## Capability classes

| Capability | Required for | Degradation if absent |
|---|---|---|
| Home Assistant event/trigger | automatic activation | manual activation |
| Camera snapshot entity | image/document capture | no image analysis |
| Local media-player output | doorstep speech | notification/log only |
| Notification target | remote awareness | local operation only |
| Ollama text model | adaptive local responses | deterministic responses |
| Local vision model | image classification/extraction | no vision |
| Encrypted local storage | protected event log | do not claim protected archive |
| Confirmed recording integration | recording claims | never say recording is active |

## Host classes

Home Assistant host compatibility and local-AI performance are separate dimensions. A host can be fully compatible with BasedDoor Lite while being unsuitable for local vision inference.

## Camera policy

Prefer Home Assistant camera entities and local integrations. ONVIF/RTSP capability is useful, but BasedDoor should consume the Home Assistant abstraction wherever possible.

### Reolink

Reolink cameras and doorbells are useful local camera inputs. Home Assistant's official Reolink integration currently lists two-way audio/Text-to-Speech as unavailable, so do **not** assume a Reolink doorbell is a BasedDoor speaker. Pair it with a separately verified local media-player/TTS output when spoken doorstep responses are required.

## Field-test matrix

Before marking an SKU supported, record:

- exact SKU and hardware revision
- firmware version
- Home Assistant version
- integration used
- snapshot PASS/FAIL
- trigger PASS/FAIL
- audio output PASS/FAIL
- local-only operation PASS/FAIL
- 25 repeated trigger cycles
- power/network interruption recovery
- AI-disabled deterministic fallback
- latency p50 / p95
- notes and evidence/log reference

Support claims should name the tested revision, not just the marketing family.
