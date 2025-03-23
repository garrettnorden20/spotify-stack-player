import random
from dotenv import load_dotenv
import keyboard
import os
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth


load_dotenv()
# Constants for Spotify API credentials
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")

# Define the scope for playback control
SCOPE = "user-modify-playback-state user-read-playback-state user-top-read"

def get_spotify_client():
    """Authenticate and return a Spotify client instance."""
    sp = Spotify(auth_manager=SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=SCOPE
    ))
    return sp


#paused_time = None
#paused_uri = None

class Controller:
    def __init__(self):
        self.play_stack = []  # Initialize an empty list
        self.paused_time = None  # Initialize pausedTime as None
        self.paused_uri = None  # Initialize pausedUri as None
        self.device_id = None
        self.last_song = None
        self.queued_song_uris = None
        self.stepped_uri = None
        self.step_in = False
        self.album_uri = None

    def clear_paused(self):
        self.paused_time = None  # Initialize pausedTime as None
        self.paused_uri = None  # Initialize pausedUri as None
        self.album_uri = None


controller = Controller()


def toggle_playback(sp: Spotify):
    """Pause playback if playing, or else resume."""
    curr_playback = sp.current_playback()
    try:
        print(curr_playback)
        #print(curr_playback['context']['uri'])
        #print(sp.playlist_items(playlist_id=curr_playback['context']['uri']))
        if controller.paused_time is None:
            controller.paused_time = curr_playback['progress_ms']
            controller.paused_uri = curr_playback['item']['uri']
            sp.pause_playback()
            print("Playback paused.")
        else:
            if controller.stepped_uri is None: # not in album, so resume from our list of queued
                sp.start_playback(controller.device_id, None, controller.queued_song_uris, {"uri": controller.paused_uri}, controller.paused_time)
            else: # resume from within our album
                sp.start_playback(controller.device_id, controller.album_uri, None, {"uri": controller.paused_uri}, controller.paused_time)
            controller.clear_paused()
            print("Playback resumed.")
    except Exception as e:
        print(f"Error toggling playback: {e}")

def next_track(sp: Spotify):
    """Skip to the next track."""
    curr_playback = sp.current_playback()
    try:
        print(sp.queue())
        if curr_playback['item']['uri'] == controller.last_song:
            queue_new(sp)
        else:
            sp.next_track()
        print("Skipped to the next track.")
    except Exception as e:
        print(f"Error skipping track: {e}")

def previous_track(sp):
    curr_playback = sp.current_playback()
    """Go back to the previous track."""
    try:
        curr_ms = curr_playback['progress_ms']
        if (curr_ms < 10000):
            sp.previous_track()
        else: 
            sp.seek_track(0)
        print("Went back to the previous track.")
    except Exception as e:
        print(f"Error going back to previous track: {e}")

def step_in(sp):
    controller.step_in = True
    curr_playback = sp.current_playback()
    try:
        print("Stepped into album.")
        controller.stepped_uri = curr_playback['item']['uri']

        controller.album_uri = curr_playback['item']['album']['uri']
        sp.start_playback(controller.device_id, controller.album_uri, None, None, None)
    except Exception as e:
        print(f"Error stepping in: {e}")

def queue_new(sp):
    curr_playback = sp.current_playback()
    try:
        # if we had stepped into an album, resume from the song where we pressed "step"
        if controller.stepped_uri is not None and controller.queued_song_uris is not None and len(controller.queued_song_uris) > 0:
            print("Stepping out")
            sp.start_playback(controller.device_id, None, controller.queued_song_uris, {"uri": controller.stepped_uri}, None)
            controller.stepped_uri = None
            controller.album_uri = None
            return
        print("Queuing new songs")

        size = 30
        tracks = random.sample(get_all_top_tracks(sp), size)
        controller.queued_song_uris = tracks
        sp.start_playback(controller.device_id, None, tracks, None, None)
        controller.last_song = tracks[size-1]

    except Exception as e:
        print(f"Error queuing new songs: {e}")

def seek_track(sp: Spotify, offset_sec):
    try:
        curr_playback = sp.current_playback()
        curr_pos_ms = curr_playback['progress_ms']
        song_dur_ms = curr_playback['item']['duration_ms']
        offset_sec_ms = offset_sec*1000
        if curr_pos_ms + offset_sec_ms < 0:
            sp.seek_track(0)
        elif curr_pos_ms + offset_sec_ms > song_dur_ms:
            return
        else:
            sp.seek_track(curr_pos_ms + offset_sec_ms)
    except Exception as e:
        print(f"Error adjusting song length: {e}")



def get_all_top_tracks(sp, max_tracks=50, batch_size=50):
    tracks, offset = [], 0
    while max_tracks is None or len(tracks) < max_tracks:
        items = sp.current_user_top_tracks(limit=batch_size, offset=offset).get('items', [])
        if not items:
            break
        tracks.extend(item['uri'] for item in items)
        offset += batch_size
    return tracks[:max_tracks] if max_tracks else tracks


def on_press(event, sp):
    """Handle keypress events."""
    try:
        if event.name == "f13":  # Replace with actual keys from the macropad
            previous_track(sp)
        elif event.name == "f15":
            next_track(sp)
        elif event.name == "f20":
            toggle_playback(sp)
        elif event.name == "f14":
            step_in(sp)
        elif event.name == "f17":
            queue_new(sp)
        elif event.name == "f16":
            seek_track(sp, -10)
        elif event.name == "f18":
            seek_track(sp, 10)
        elif event.name == "f23":
            return # DJ???
    except Exception as e:
        print(f"Error handling key press: {e}")

def main():
    sp = get_spotify_client()
    print("Spotify controller started. Press keys to control playback:")
    print("F6: Previous Track, F8: Next Track, F7: Pause")

    controller.device_id = sp.current_playback()['device']['id']

    # Set up keyboard hooks
    keyboard.on_press(lambda event: on_press(event, sp))

    # Keep the program running
    keyboard.wait('esc')  # Use 'esc' to exit the program

if __name__ == "__main__":
    main()
