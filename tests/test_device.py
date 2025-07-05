import sys
import types
import unittest
from unittest.mock import MagicMock
import importlib.util
import os

# Provide lightweight stubs for optional dependencies used in main
sys.modules.setdefault("keyboard", types.ModuleType("keyboard"))
spotipy_stub = types.ModuleType("spotipy")
spotipy_stub.Spotify = object
oauth2_stub = types.ModuleType("oauth2")
oauth2_stub.SpotifyOAuth = object
spotipy_stub.oauth2 = oauth2_stub
sys.modules.setdefault("spotipy", spotipy_stub)
sys.modules.setdefault("spotipy.oauth2", oauth2_stub)

spec = importlib.util.spec_from_file_location(
    "main", os.path.join(os.path.dirname(__file__), "..", "main.py")
)
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)
get_device_id = main.get_device_id


class GetDeviceIDTests(unittest.TestCase):
    def test_uses_current_playback_device(self):
        sp = MagicMock()
        sp.current_playback.return_value = {"device": {"id": "abc123"}}
        self.assertEqual(get_device_id(sp), "abc123")

    def test_falls_back_to_first_device(self):
        sp = MagicMock()
        sp.current_playback.return_value = None
        sp.devices.return_value = {"devices": [{"id": "d1"}, {"id": "d2"}]}
        self.assertEqual(get_device_id(sp), "d1")

    def test_no_devices_raises_error(self):
        sp = MagicMock()
        sp.current_playback.return_value = None
        sp.devices.return_value = {"devices": []}
        with self.assertRaises(RuntimeError):
            get_device_id(sp)


if __name__ == "__main__":
    unittest.main()
