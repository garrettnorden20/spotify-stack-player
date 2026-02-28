import tkinter as tk
import queue
import threading
from tkinter import ttk
from typing import Callable, Dict, Optional

from .controller import SpotifyStackController


class SpotifyStackApp:
    def __init__(
        self,
        root: tk.Tk,
        controller: SpotifyStackController,
        enable_hotkeys: bool = False,
        register_hotkeys: Optional[Callable[[Dict[str, Callable[[], None]]], str]] = None,
    ):
        self.root = root
        self.controller = controller

        self.root.title("Spotify Stack Player")
        self.root.geometry("700x400")
        self.root.minsize(700, 400)
        self.root.configure(padx=10, pady=10)

        self.status_var = tk.StringVar(value="Ready")
        self.track_var = tk.StringVar(value="No active playback")
        self.context_var = tk.StringVar(value="Context: -")
        self.stack_depth_var = tk.StringVar(value="Stack depth: 0")
        self._ui_queue: queue.Queue = queue.Queue()
        self._refresh_inflight = False
        self._refresh_pending = False

        self._build_ui()
        self._pump_ui_queue()

        if enable_hotkeys and register_hotkeys:
            self._enable_hotkeys(register_hotkeys)

        self._request_refresh()

    def _enable_hotkeys(self, register_hotkeys):
        handlers = {
            "previous_track": lambda: self.root.after(0, lambda: self._run_action(self.controller.previous_track)),
            "next_track": lambda: self.root.after(0, lambda: self._run_action(self.controller.next_track)),
            "toggle_playback": lambda: self.root.after(0, lambda: self._run_action(self.controller.toggle_playback)),
            "hop_in_album": lambda: self.root.after(0, lambda: self._run_action(self.controller.hop_in_album)),
            "hop_out": lambda: self.root.after(0, lambda: self._run_action(self.controller.hop_out)),
            "queue_new_from_top_tracks": lambda: self.root.after(
                0, lambda: self._run_action(self.controller.queue_new_from_top_tracks)
            ),
            "seek_back": lambda: self.root.after(0, lambda: self._run_action(lambda: self.controller.seek_relative(-10))),
            "seek_forward": lambda: self.root.after(0, lambda: self._run_action(lambda: self.controller.seek_relative(10))),
        }

        status = register_hotkeys(handlers)
        self.status_var.set(status)

    def _build_ui(self):
        top = ttk.Frame(self.root, padding=(4, 2))
        top.pack(fill="x")

        ttk.Label(
            top,
            textvariable=self.track_var,
            font=("Avenir Next", 15, "bold"),
            anchor="w",
        ).pack(fill="x")
        ttk.Label(
            top,
            textvariable=self.context_var,
            anchor="w",
        ).pack(fill="x")
        ttk.Label(
            top,
            textvariable=self.stack_depth_var,
            anchor="w",
        ).pack(fill="x")

        controls = ttk.Frame(self.root, padding=(4, 6))
        controls.pack(fill="x")

        buttons = [
            ("⏮ Prev", self.controller.previous_track),
            ("⏯ Play/Pause", self.controller.toggle_playback),
            ("Next ⏭", self.controller.next_track),
            ("⌁ Queue Top", self.controller.queue_new_from_top_tracks),
            ("⏪/+10 Split", None),
            ("↳ Hop In Here", self.controller.hop_in_album),
            ("↳ Hop In Start", lambda: self.controller.hop_in_album(from_start=True)),
            ("↲ Hop Out", self.controller.hop_out),
        ]

        for col in range(4):
            controls.grid_columnconfigure(col, weight=1)
        for idx, (text, action) in enumerate(buttons):
            row = idx // 4
            col = idx % 4
            if text == "⏪/+10 Split":
                split = ttk.Frame(controls)
                split.grid(row=row, column=col, padx=6, pady=6, sticky="ew")
                split.grid_columnconfigure(0, weight=1)
                split.grid_columnconfigure(1, weight=1)
                ttk.Button(
                    split,
                    text="-10s",
                    command=lambda: self._run_action(lambda: self.controller.seek_relative(-10)),
                ).grid(row=0, column=0, sticky="ew")
                ttk.Button(
                    split,
                    text="+10s",
                    command=lambda: self._run_action(lambda: self.controller.seek_relative(10)),
                ).grid(row=0, column=1, sticky="ew")
            else:
                ttk.Button(
                    controls,
                    text=text,
                    width=16,
                    command=lambda a=action: self._run_action(a),
                ).grid(row=row, column=col, padx=6, pady=6, sticky="ew")

        middle = ttk.Frame(self.root, padding=(4, 4))
        middle.pack(fill="both", expand=True)

        ttk.Label(
            middle,
            text="Stack Frames",
            anchor="w",
            font=("Avenir Next", 11, "bold"),
        ).pack(fill="x")
        stack_frame = ttk.Frame(middle)
        stack_frame.pack(fill="both", expand=True)

        self.stack_list = tk.Listbox(
            stack_frame,
            height=10,
            activestyle="none",
            bd=0,
            highlightthickness=1,
            font=("Menlo", 11),
        )
        self.stack_list.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(stack_frame, orient="vertical", command=self.stack_list.yview)
        scrollbar.pack(side="right", fill="y")
        self.stack_list.config(yscrollcommand=scrollbar.set)
        self.stack_list.insert(tk.END, "(empty)")

        bottom = ttk.Frame(self.root, padding=(4, 2))
        bottom.pack(fill="x")
        ttk.Label(
            bottom,
            textvariable=self.status_var,
            anchor="w",
            font=("Avenir Next", 10),
        ).pack(fill="x")

    def _run_action(self, action):
        self.status_var.set("Working...")

        def worker():
            try:
                result = action()
                self._ui_queue.put(("action_ok", result))
            except Exception as exc:
                self._ui_queue.put(("action_err", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _pump_ui_queue(self):
        while True:
            try:
                event, payload = self._ui_queue.get_nowait()
            except queue.Empty:
                break

            if event == "action_ok":
                self.status_var.set(payload)
                self._request_refresh(force=True)
            elif event == "action_err":
                self.status_var.set(f"Error: {payload}")
                self._request_refresh(force=True)
            elif event == "refresh_ok":
                self._apply_refresh_state(payload)
            elif event == "refresh_err":
                self.status_var.set(f"Refresh error: {payload}")
                self._refresh_inflight = False
                if self._refresh_pending:
                    self._refresh_pending = False
                    self._request_refresh()

        self.root.after(100, self._pump_ui_queue)

    def _apply_refresh_state(self, data):
        playback = data.get("playback")
        stack_lines = data.get("stack_lines", [])
        stack_depth = data.get("stack_depth", 0)
        force = data.get("force", False)

        if playback and playback.get("item"):
            item = playback["item"]
            artists = ", ".join(a["name"] for a in item.get("artists", []))
            self.track_var.set(f"{item.get('name')} - {artists}")

            context = self.controller.describe_playback_source(playback)
            progress = playback.get("progress_ms", 0) // 1000
            self.context_var.set(f"Context: {context} | t={progress}s")
        elif force:
            self.track_var.set("No active playback")
            self.context_var.set("Context: -")

        self.stack_list.delete(0, tk.END)
        for line in stack_lines:
            self.stack_list.insert(tk.END, line)
        self.stack_depth_var.set(f"Stack depth: {stack_depth}")

        self._refresh_inflight = False
        if self._refresh_pending:
            self._refresh_pending = False
            self._request_refresh()
        else:
            self.root.after(3000, self._request_refresh)

    def _request_refresh(self, force: bool = False):
        if self._refresh_inflight:
            self._refresh_pending = True
            return

        self._refresh_inflight = True

        def worker():
            try:
                playback = self.controller.current_playback()
                stack_lines = self.controller.stack_summary()
                stack_depth = len(self.controller.stack)
                self._ui_queue.put(
                    (
                        "refresh_ok",
                        {
                            "playback": playback,
                            "stack_lines": stack_lines,
                            "stack_depth": stack_depth,
                            "force": force,
                        },
                    )
                )
            except Exception as exc:
                self._ui_queue.put(("refresh_err", str(exc)))

        threading.Thread(target=worker, daemon=True).start()
