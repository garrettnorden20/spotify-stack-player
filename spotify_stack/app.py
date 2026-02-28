import os
import tkinter as tk

from dotenv import load_dotenv
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth

from .controller import SpotifyStackController
from .hotkeys import HotkeyManager
from .ui import SpotifyStackApp


SCOPE = (
    "user-modify-playback-state "
    "user-read-playback-state "
    "user-top-read "
    "playlist-read-private "
    "playlist-read-collaborative"
)
TOKEN_CACHE_PATH = os.getenv(
    "SPOTIFY_TOKEN_CACHE_PATH",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), ".spotify_token_cache"),
)


def get_spotify_client() -> Spotify:
    # Force .env values to override any stale exported shell variables.
    load_dotenv(override=True)
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI") or ""
    if "developer.spotify.com" in redirect_uri:
        raise RuntimeError(
            "Invalid SPOTIFY_REDIRECT_URI for this app flow. "
            "Use http://127.0.0.1:8888/callback in both .env and Spotify app settings."
        )

    return Spotify(
        auth_manager=SpotifyOAuth(
            client_id=os.getenv("SPOTIFY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
            redirect_uri=redirect_uri,
            scope=SCOPE,
            cache_path=TOKEN_CACHE_PATH,
        )
    )


def run_app(enable_hotkeys: bool = True):
    sp = get_spotify_client()
    controller = SpotifyStackController(sp)

    root = tk.Tk()
    hotkey_manager = HotkeyManager(handlers={})

    def register_hotkeys(handlers):
        hotkey_manager.handlers = handlers
        return hotkey_manager.start()

    _app = SpotifyStackApp(
        root,
        controller,
        enable_hotkeys=enable_hotkeys,
        register_hotkeys=register_hotkeys,
    )

    def on_close():
        hotkey_manager.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
