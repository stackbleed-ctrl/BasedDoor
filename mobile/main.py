"""
BasedDoor Mobile — Main App Entry Point
Android-first portable rights assistant.
Built with Kivy for cross-platform APK via Buildozer.
"""
from __future__ import annotations

import os
import json
import threading
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle

from hotword_listener import HotwordListener
from response_engine import ResponseEngine

# ── Colours ─────────────────────────────────────────────────────────────────
COLOUR_BG        = (0.05, 0.05, 0.08, 1)   # near-black
COLOUR_RED       = (0.85, 0.15, 0.15, 1)   # alert red
COLOUR_GREEN     = (0.1,  0.75, 0.35, 1)   # active green
COLOUR_AMBER     = (0.95, 0.65, 0.0,  1)   # standby amber
COLOUR_TEXT      = (0.95, 0.95, 0.95, 1)   # off-white
COLOUR_SUBTEXT   = (0.55, 0.55, 0.65, 1)

CONFIG_PATH = Path(__file__).parent / "config.json"

DEFAULT_CONFIG = {
    "ollama_endpoint":  "http://192.168.1.100:11434",
    "ollama_model":     "llama3.2:3b",
    "piper_endpoint":   "http://192.168.1.100:5000",
    "mode":             "polite_canadian",
    "offline_mode":     True,
    "hotword":          "Hey Door",
    "wireguard":        False,
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text())
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


# ── UI ───────────────────────────────────────────────────────────────────────

class BasedDoorApp(App):
    title = "BasedDoor"

    def build(self):
        self.config = load_config()
        self.engine = ResponseEngine(self.config)
        self.hotword = HotwordListener(
            phrase=self.config.get("hotword", "Hey Door"),
            callback=self._on_hotword,
        )

        Window.clearcolor = COLOUR_BG

        root = BoxLayout(orientation="vertical", padding=20, spacing=15)

        # ── Header ───────────────────────────────────────────────────────────
        self.status_label = Label(
            text="● STANDBY",
            font_size="22sp",
            color=COLOUR_AMBER,
            bold=True,
            size_hint=(1, 0.1),
        )
        root.add_widget(self.status_label)

        self.info_label = Label(
            text=f'Say "{self.config["hotword"]}" or press ACTIVATE',
            font_size="14sp",
            color=COLOUR_SUBTEXT,
            size_hint=(1, 0.08),
        )
        root.add_widget(self.info_label)

        # ── Response display ─────────────────────────────────────────────────
        self.response_label = Label(
            text="",
            font_size="16sp",
            color=COLOUR_TEXT,
            text_size=(Window.width - 60, None),
            halign="center",
            valign="middle",
            size_hint=(1, 0.3),
        )
        root.add_widget(self.response_label)

        # ── Mode selector ────────────────────────────────────────────────────
        mode_row = BoxLayout(orientation="horizontal", size_hint=(1, 0.1), spacing=10)
        mode_row.add_widget(Label(text="Mode:", color=COLOUR_SUBTEXT, size_hint=(0.25, 1)))
        self.mode_spinner = Spinner(
            text=self.config.get("mode", "polite_canadian"),
            values=["polite_canadian", "grok_based", "maximum_refusal", "user_clip"],
            size_hint=(0.75, 1),
        )
        self.mode_spinner.bind(text=self._on_mode_change)
        mode_row.add_widget(self.mode_spinner)
        root.add_widget(mode_row)

        # ── Buttons ──────────────────────────────────────────────────────────
        btn_row = BoxLayout(orientation="horizontal", size_hint=(1, 0.15), spacing=10)

        self.activate_btn = Button(
            text="ACTIVATE",
            font_size="18sp",
            background_color=COLOUR_RED,
            bold=True,
            size_hint=(0.6, 1),
        )
        self.activate_btn.bind(on_press=self._on_activate_pressed)
        btn_row.add_widget(self.activate_btn)

        offline_btn = Button(
            text="OFFLINE" if self.config.get("offline_mode") else "ONLINE",
            font_size="14sp",
            background_color=COLOUR_GREEN,
            size_hint=(0.4, 1),
        )
        offline_btn.bind(on_press=self._toggle_offline)
        self.offline_btn = offline_btn
        btn_row.add_widget(offline_btn)

        root.add_widget(btn_row)

        # ── Footer ───────────────────────────────────────────────────────────
        footer = Label(
            text="🍁 BasedDoor | Charter s.7 & s.8 | Recording: OFF",
            font_size="11sp",
            color=COLOUR_SUBTEXT,
            size_hint=(1, 0.06),
        )
        self.footer_label = footer
        root.add_widget(footer)

        # Start hotword listener
        threading.Thread(target=self.hotword.start, daemon=True).start()

        return root

    def _set_active(self, active: bool):
        if active:
            self.status_label.text = "🔴 ACTIVE — Recording"
            self.status_label.color = COLOUR_RED
            self.footer_label.text = "🍁 BasedDoor | Charter s.7 & s.8 | Recording: ON"
        else:
            self.status_label.text = "● STANDBY"
            self.status_label.color = COLOUR_AMBER
            self.footer_label.text = "🍁 BasedDoor | Charter s.7 & s.8 | Recording: OFF"

    def _on_hotword(self):
        """Called from hotword thread — schedule on main thread."""
        Clock.schedule_once(lambda dt: self._trigger_response(), 0)

    def _on_activate_pressed(self, *_):
        self._trigger_response()

    def _trigger_response(self):
        self._set_active(True)
        self.response_label.text = "Generating response..."
        threading.Thread(target=self._run_response, daemon=True).start()

    def _run_response(self):
        text = self.engine.respond(
            mode=self.config.get("mode", "polite_canadian"),
            offline=self.config.get("offline_mode", True),
        )
        Clock.schedule_once(lambda dt: self._show_response(text), 0)

    def _show_response(self, text: str):
        self.response_label.text = text
        Clock.schedule_once(lambda dt: self._set_active(False), 8)

    def _on_mode_change(self, spinner, text):
        self.config["mode"] = text
        save_config(self.config)

    def _toggle_offline(self, btn):
        self.config["offline_mode"] = not self.config.get("offline_mode", True)
        btn.text = "OFFLINE" if self.config["offline_mode"] else "ONLINE"
        save_config(self.config)


if __name__ == "__main__":
    BasedDoorApp().run()
