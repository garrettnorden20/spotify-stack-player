import random
from dataclasses import dataclass
from typing import List, Optional

try:
    from spotipy import Spotify
except ImportError:  # pragma: no cover
    Spotify = object  # type: ignore


@dataclass
class PlaybackFrame:
    context_uri: Optional[str]
    track_uri: Optional[str]
    progress_ms: int
    resume_uris: Optional[List[str]]
    track_name: str
    artist_names: str
    source_label: str


class SpotifyStackController:
    def __init__(self, sp: Spotify):
        self.sp = sp
        self.stack: List[PlaybackFrame] = []
        self.active_uris: List[str] = []

    def current_playback(self):
        return self.sp.current_playback()

    def _active_device_id(self) -> Optional[str]:
        playback = self.current_playback()
        if playback and playback.get("device"):
            return playback["device"].get("id")

        devices = self.sp.devices().get("devices", [])
        if devices:
            active = next((d for d in devices if d.get("is_active")), devices[0])
            return active.get("id")
        return None

    def _start_playback(
        self,
        context_uri: Optional[str] = None,
        uris: Optional[List[str]] = None,
        offset: Optional[dict] = None,
        position_ms: Optional[int] = None,
    ):
        self.sp.start_playback(
            device_id=self._active_device_id(),
            context_uri=context_uri,
            uris=uris,
            offset=offset,
            position_ms=position_ms,
        )

    def _snapshot_resume_uris(self) -> Optional[List[str]]:
        uris: List[str] = []
        try:
            queue_response = self.sp.queue()
            current = queue_response.get("currently_playing")
            if current and current.get("uri"):
                uris.append(current["uri"])
            for item in queue_response.get("queue", []):
                uri = item.get("uri")
                if uri:
                    uris.append(uri)
        except Exception:
            uris = []

        if not uris and self.active_uris:
            uris = self.active_uris[:]

        if not uris:
            return None

        deduped: List[str] = []
        seen = set()
        for uri in uris:
            if uri not in seen:
                deduped.append(uri)
                seen.add(uri)
        return deduped[:100]

    def _source_label_from_context(self, context_uri: Optional[str]) -> str:
        label = context_uri or "Ad-hoc queue"
        if label.startswith("spotify:"):
            parts = label.split(":")
            if len(parts) >= 3:
                return f"{parts[1]}:{parts[2]}"
        return label

    def _build_frame_from_playback(self, playback: dict) -> PlaybackFrame:
        item = playback.get("item") or {}
        artists = item.get("artists") or []
        context_uri = (playback.get("context") or {}).get("uri")
        return PlaybackFrame(
            context_uri=context_uri,
            track_uri=item.get("uri"),
            progress_ms=playback.get("progress_ms", 0),
            resume_uris=self._snapshot_resume_uris(),
            track_name=item.get("name") or "Unknown track",
            artist_names=", ".join(artist.get("name", "") for artist in artists) or "Unknown artist",
            source_label=self._source_label_from_context(context_uri),
        )

    def toggle_playback(self):
        playback = self.current_playback()
        if not playback:
            return "No active playback."
        if playback.get("is_playing"):
            self.sp.pause_playback(device_id=self._active_device_id())
            return "Paused"
        self.sp.start_playback(device_id=self._active_device_id())
        return "Playing"

    def next_track(self):
        self.sp.next_track(device_id=self._active_device_id())
        return "Skipped"

    def previous_track(self):
        playback = self.current_playback()
        if not playback:
            return "No active playback."

        if playback.get("progress_ms", 0) < 10_000:
            self.sp.previous_track(device_id=self._active_device_id())
        else:
            self.sp.seek_track(position_ms=0, device_id=self._active_device_id())
        return "Previous"

    def seek_relative(self, delta_seconds: int):
        playback = self.current_playback()
        if not playback or not playback.get("item"):
            return "No active playback."

        progress = playback.get("progress_ms", 0)
        duration = playback["item"].get("duration_ms", 0)
        target = max(0, min(duration, progress + (delta_seconds * 1000)))
        self.sp.seek_track(position_ms=target, device_id=self._active_device_id())
        return f"Seeked to {target // 1000}s"

    def queue_new_from_top_tracks(self, size: int = 30):
        playback = self.current_playback()
        if playback and playback.get("item"):
            # Entering a new ad-hoc queue should be stack-aware.
            self.stack.append(self._build_frame_from_playback(playback))

        tracks = self.get_all_top_tracks(max_tracks=200)
        if len(tracks) < size:
            size = len(tracks)
        if size == 0:
            if playback and playback.get("item") and self.stack:
                self.stack.pop()
            return "No top tracks available."

        selection = random.sample(tracks, size)
        self.active_uris = selection
        self._start_playback(uris=selection)
        return f"Entered queue: shuffled top {size}"

    def get_all_top_tracks(self, max_tracks: int = 200, batch_size: int = 50) -> List[str]:
        tracks: List[str] = []
        offset = 0

        while len(tracks) < max_tracks:
            response = self.sp.current_user_top_tracks(limit=batch_size, offset=offset)
            items = response.get("items", [])
            if not items:
                break
            tracks.extend(item["uri"] for item in items)
            offset += batch_size

        return tracks[:max_tracks]

    def hop_in_album(self):
        playback = self.current_playback()
        if not playback or not playback.get("item"):
            return "No active playback."

        item = playback["item"]
        frame = self._build_frame_from_playback(playback)
        self.stack.append(frame)

        album_uri = (item.get("album") or {}).get("uri")
        if not album_uri:
            self.stack.pop()
            return "Current track has no album URI."

        self._start_playback(
            context_uri=album_uri,
            offset={"uri": item.get("uri")},
            position_ms=playback.get("progress_ms", 0),
        )
        return f"Hop in: {album_uri}"

    def hop_out(self):
        if not self.stack:
            return "Stack is empty."

        frame = self.stack[-1]

        if frame.context_uri and frame.track_uri:
            self._start_playback(
                context_uri=frame.context_uri,
                offset={"uri": frame.track_uri},
                position_ms=frame.progress_ms,
            )
            self.stack.pop()
            return "Hop out: resumed context"

        if frame.resume_uris and frame.track_uri:
            self.active_uris = frame.resume_uris
            offset_uri = frame.track_uri if frame.track_uri in frame.resume_uris else frame.resume_uris[0]
            self._start_playback(uris=frame.resume_uris, offset={"uri": offset_uri}, position_ms=frame.progress_ms)
            self.stack.pop()
            return "Hop out: resumed queue snapshot"

        return "Hop out failed: no resumable frame"

    def stack_summary(self) -> List[str]:
        if not self.stack:
            return ["(empty)"]

        lines = []
        for idx, frame in enumerate(reversed(self.stack), start=1):
            minutes, seconds = divmod(frame.progress_ms // 1000, 60)
            lines.append(
                f"{idx}. {frame.track_name} - {frame.artist_names} | from {frame.source_label} @ {minutes:02d}:{seconds:02d}"
            )
        return lines
