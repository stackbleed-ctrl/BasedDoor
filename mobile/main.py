"""BasedDoor Mobile — conservative Android-first client."""
from __future__ import annotations

import json
import threading
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner

from response_engine import ResponseEngine

CONFIG_PATH = Path(__file__).parent / "config.json"
DEFAULT_CONFIG = {
    "ollama_endpoint": "",
    "ollama_model": "llama3.2:3b",
    "mode": "polite_canadian",
    "offline_mode": True,
}


def load_config() -> dict:
    try:
        if CONFIG_PATH.exists():
            return {**DEFAULT_CONFIG, **json.loads(CONFIG_PATH.read_text())}
    except Exception:
        pass
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


class BasedDoorApp(App):
    title = "BasedDoor"

    def build(self):
        self.settings = load_config()
        self.engine = ResponseEngine(self.settings)

        root = BoxLayout(orientation="vertical", padding=24, spacing=16)

        self.status = Label(
            text="READY — recording not enabled",
            font_size="20sp",
            size_hint=(1, .14),
        )
        root.add_widget(self.status)

        root.add_widget(Label(
            text=(
                "Local-first doorstep response assistant.\n"
                "Press ACTIVATE to play the configured response.\n"
                "This build does not claim to record audio or video."
            ),
            halign="center",
            size_hint=(1, .28),
        ))

        self.response = Label(text="", halign="center", size_hint=(1, .24))
        root.add_widget(self.response)

        self.mode = Spinner(
            text=self.settings.get("mode", "polite_canadian"),
            values=("polite_canadian", "grok_based", "maximum_refusal"),
            size_hint=(1, .12),
        )
        self.mode.bind(text=self._change_mode)
        root.add_widget(self.mode)

        activate = Button(text="ACTIVATE", font_size="20sp", size_hint=(1, .16))
        activate.bind(on_press=self._activate)
        root.add_widget(activate)

        return root

    def _change_mode(self, _spinner, text):
        self.settings["mode"] = text
        save_config(self.settings)

    def _activate(self, *_):
        self.status.text = "ACTIVE — preparing response"
        self.response.text = ""
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        text = self.engine.respond(
            mode=self.settings.get("mode", "polite_canadian"),
            offline=self.settings.get("offline_mode", True),
        )
        Clock.schedule_once(lambda _dt: self._show(text), 0)

    def _show(self, text):
        self.response.text = text
        self.status.text = "READY — recording not enabled"


if __name__ == "__main__":
    BasedDoorApp().run()
