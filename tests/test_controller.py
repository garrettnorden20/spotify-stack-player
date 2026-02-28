import unittest
from unittest.mock import Mock

from spotify_stack.controller import SpotifyStackController


class SpotifyStackControllerTests(unittest.TestCase):
    def make_sp(self):
        sp = Mock()
        sp.current_playback.return_value = {
            "is_playing": True,
            "progress_ms": 42000,
            "context": {"uri": "spotify:playlist:abc"},
            "device": {"id": "dev123"},
            "item": {
                "uri": "spotify:track:t1",
                "duration_ms": 180000,
                "album": {"uri": "spotify:album:a1"},
                "artists": [{"name": "A"}],
                "name": "Track 1",
            },
        }
        sp.devices.return_value = {"devices": [{"id": "dev123", "is_active": True}]}
        sp.playlist.return_value = {"name": "My Playlist"}
        sp.album.return_value = {"name": "Album A"}
        sp.artist.return_value = {"name": "Artist A"}
        sp.queue.return_value = {
            "currently_playing": {"uri": "spotify:track:t1"},
            "queue": [{"uri": "spotify:track:t2"}],
        }
        return sp

    def test_hop_in_pushes_frame_and_switches_to_album(self):
        sp = self.make_sp()
        controller = SpotifyStackController(sp)

        result = controller.hop_in_album()

        self.assertEqual(result, "Hop in: spotify:album:a1")
        self.assertEqual(len(controller.stack), 1)
        frame = controller.stack[-1]
        self.assertEqual(frame.context_uri, "spotify:playlist:abc")
        self.assertEqual(frame.track_uri, "spotify:track:t1")
        self.assertEqual(frame.progress_ms, 42000)
        self.assertEqual(frame.source_label, "My Playlist")
        self.assertEqual(frame.track_name, "Track 1")

        sp.start_playback.assert_called_once_with(
            device_id="dev123",
            context_uri="spotify:album:a1",
            uris=None,
            offset={"uri": "spotify:track:t1"},
            position_ms=42000,
        )

    def test_hop_in_from_start_uses_first_album_track(self):
        sp = self.make_sp()
        controller = SpotifyStackController(sp)

        result = controller.hop_in_album(from_start=True)

        self.assertEqual(result, "Hop in start: spotify:album:a1")
        sp.start_playback.assert_called_once_with(
            device_id="dev123",
            context_uri="spotify:album:a1",
            uris=None,
            offset={"position": 0},
            position_ms=0,
        )

    def test_hop_out_restores_previous_context(self):
        sp = self.make_sp()
        controller = SpotifyStackController(sp)
        controller.hop_in_album()
        sp.start_playback.reset_mock()

        result = controller.hop_out()

        self.assertEqual(result, "Hop out: resumed context")
        self.assertEqual(len(controller.stack), 0)
        sp.start_playback.assert_called_once_with(
            device_id="dev123",
            context_uri="spotify:playlist:abc",
            uris=None,
            offset={"uri": "spotify:track:t1"},
            position_ms=42000,
        )

    def test_hop_out_restores_queue_when_no_context(self):
        sp = self.make_sp()
        playback = sp.current_playback.return_value
        playback["context"] = None

        controller = SpotifyStackController(sp)
        controller.hop_in_album()
        sp.start_playback.reset_mock()

        result = controller.hop_out()

        self.assertEqual(result, "Hop out: resumed queue snapshot")
        sp.start_playback.assert_called_once_with(
            device_id="dev123",
            context_uri=None,
            uris=["spotify:track:t1", "spotify:track:t2"],
            offset={"uri": "spotify:track:t1"},
            position_ms=42000,
        )

    def test_seek_relative_clamps_to_song_duration(self):
        sp = self.make_sp()
        controller = SpotifyStackController(sp)

        result = controller.seek_relative(999)

        self.assertEqual(result, "Seeked to 180s")
        sp.seek_track.assert_called_once_with(position_ms=180000, device_id="dev123")

    def test_queue_top_enters_new_stack_frame(self):
        sp = self.make_sp()
        controller = SpotifyStackController(sp)
        controller.get_all_top_tracks = Mock(return_value=["spotify:track:x1", "spotify:track:x2", "spotify:track:x3"])

        result = controller.queue_new_from_top_tracks(size=2)

        self.assertTrue(result.startswith("Entered queue: shuffled top"))
        self.assertEqual(len(controller.stack), 1)
        frame = controller.stack[0]
        self.assertEqual(frame.track_uri, "spotify:track:t1")
        self.assertEqual(frame.source_label, "My Playlist")
        sp.start_playback.assert_called_once()

    def test_hop_out_returns_to_album_after_queue_top(self):
        sp = self.make_sp()
        playback = sp.current_playback.return_value
        playback["context"] = {"uri": "spotify:album:a1"}
        playback["item"]["album"] = {"uri": "spotify:album:a1"}
        playback["item"]["uri"] = "spotify:track:a_song"
        playback["item"]["name"] = "Album Song"
        sp.queue.return_value = {
            "currently_playing": {"uri": "spotify:track:a_song"},
            "queue": [{"uri": "spotify:track:a_next"}],
        }

        controller = SpotifyStackController(sp)
        controller.get_all_top_tracks = Mock(return_value=["spotify:track:q1", "spotify:track:q2", "spotify:track:q3"])

        controller.queue_new_from_top_tracks(size=2)
        sp.start_playback.reset_mock()
        result = controller.hop_out()

        self.assertEqual(result, "Hop out: resumed context")
        sp.start_playback.assert_called_once_with(
            device_id="dev123",
            context_uri="spotify:album:a1",
            uris=None,
            offset={"uri": "spotify:track:a_song"},
            position_ms=42000,
        )

    def test_hop_out_keeps_stack_if_restore_fails(self):
        sp = self.make_sp()
        controller = SpotifyStackController(sp)
        controller.hop_in_album()
        sp.start_playback.side_effect = RuntimeError("restore failed")

        with self.assertRaises(RuntimeError):
            controller.hop_out()

        self.assertEqual(len(controller.stack), 1)

    def test_stack_summary_is_human_readable(self):
        sp = self.make_sp()
        controller = SpotifyStackController(sp)
        controller.hop_in_album()

        summary = controller.stack_summary()

        self.assertEqual(
            summary[0],
            "1. Track 1 - A | from My Playlist @ 00:42",
        )

    def test_describe_source_shows_top_queue_for_queue_playback(self):
        sp = self.make_sp()
        playback = sp.current_playback.return_value
        playback["context"] = None
        controller = SpotifyStackController(sp)
        controller.active_uris = ["spotify:track:t1", "spotify:track:t2"]

        source = controller.describe_playback_source(playback)

        self.assertEqual(source, "Top Queue")

    def test_hop_in_from_top_queue_stores_top_queue_frame_label(self):
        sp = self.make_sp()
        playback = sp.current_playback.return_value
        playback["context"] = None
        controller = SpotifyStackController(sp)
        controller.active_uris = ["spotify:track:t1", "spotify:track:t2"]

        controller.hop_in_album()

        self.assertEqual(controller.stack[-1].source_label, "Top Queue")


if __name__ == "__main__":
    unittest.main()
