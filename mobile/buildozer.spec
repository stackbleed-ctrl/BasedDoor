[app]
title = BasedDoor
package.name = baseddoor
package.domain = ca.baseddoor
source.dir = .
source.include_exts = py,json,png,jpg,kv,wav
version = 0.2.0
requirements = python3,kivy,httpx,plyer
orientation = portrait
fullscreen = 0

# Conservative Alpha 0.2: microphone/camera permissions are intentionally
# omitted until those capabilities are implemented and truthfully surfaced.
android.permissions = INTERNET
android.api = 35
android.minapi = 26
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
