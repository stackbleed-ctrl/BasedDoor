# BasedDoor — Ring Doorbell Notes

## The 2026 Reality

Ring's official Home Assistant integration is **cloud-dependent** — events and
snapshots route through Amazon's AWS before reaching HA. There is no official
local RTSP stream.

Ring-MQTT improves event responsiveness but does **not** eliminate the cloud
dependency. You still need an active Ring account and internet connectivity.

**Amazon has complied with law enforcement data requests without notifying users.**
This is documented and ongoing.

## Using Ring with BasedDoor (Not Recommended)

If you must use Ring:

1. Install [Ring-MQTT Add-on](https://github.com/tsightler/ring-mqtt)
2. Use `automations/ring_doorbell.yaml`
3. Know that your door footage is stored on Amazon's servers

Ring-MQTT provides faster motion/ding events via local MQTT broker,
but the underlying camera stream still transits Ring's infrastructure.

## The Honest Recommendation

Running a Charter rights tool on an Amazon camera has an irony problem.

A Reolink Video Doorbell PoE costs approximately the same as a month of Ring
Protect and gives you:
- Full local RTSP stream
- No account required
- No cloud
- PoE (reliable, no WiFi dropouts)
- Built-in speaker for BasedDoor TTS output

See `docs/HARDWARE.md` for full alternatives.
