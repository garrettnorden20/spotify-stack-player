from typing import Callable, Dict, Optional


KEYMAP = {
    "f13": "previous_track",
    "f15": "next_track",
    "f20": "toggle_playback",
    "f14": "hop_in_album",
    "f19": "hop_out",
    "f17": "queue_new_from_top_tracks",
    "f16": "seek_back",
    "f18": "seek_forward",
}


class HotkeyManager:
    def __init__(self, handlers: Dict[str, Callable[[], None]]):
        self.handlers = handlers
        self._keyboard = None
        self._hook = None

    def start(self) -> Optional[str]:
        try:
            import keyboard  # type: ignore

            self._keyboard = keyboard
            self._hook = keyboard.on_press(self._on_press)
            return "Global hotkeys active (F13/F14/F15/F16/F17/F18/F19/F20)."
        except Exception as exc:
            return f"Global hotkeys unavailable: {exc}"

    def stop(self):
        if self._keyboard and self._hook:
            self._keyboard.unhook(self._hook)
            self._hook = None

    def _on_press(self, event):
        action_name = KEYMAP.get(event.name)
        if not action_name:
            return

        handler = self.handlers.get(action_name)
        if handler:
            handler()
