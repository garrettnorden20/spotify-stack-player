# Spotify Stack Player

Spotify Stack Player is a desktop Spotify controller focused on one workflow:

- `Hop In Album`: jump from your current track context into the album.
- `Hop Out`: return to the exact prior playback frame.

It maintains a playback stack so you can nest jumps and unwind back out.

## Requirements

- macOS
- A Spotify Premium account (required for playback control API)
- A Spotify Developer app (client id/secret)
- Python with Tk support

## 1. Install Python (Tk-enabled)

If your current `python3` cannot import `tkinter`, install Python from python.org.

1. Download and install a recent Python 3.12+ macOS installer:
   - [https://www.python.org/downloads/macos/](https://www.python.org/downloads/macos/)
2. Verify Tk works:

```bash
python3 -c "import tkinter as tk; print('Tk OK', tk.TkVersion)"
```

## 2. Create Virtual Environment

From project root:

```bash
cd <project-root>
python3 -m venv .venv-tk
source .venv-tk/bin/activate
python -m pip install --upgrade pip
python -m pip install spotipy python-dotenv keyboard "urllib3<2"
```

## 3. Configure Spotify Developer App

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
2. Open your app (or create one).
3. In app settings, add this Redirect URI exactly:
   - `http://127.0.0.1:8888/callback`
4. Save settings.

## 4. Configure `.env`

Create/update `<project-root>/.env`:

```env
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
```

## 5. First Launch

```bash
cd <project-root>
source .venv-tk/bin/activate
python main.py
```

Expected first-run behavior:
- Browser opens Spotify auth once.
- After approval, token is cached in `.spotify_token_cache`.
- Next runs should not require repeated login.

If auth got stuck before, clear cache once:

```bash
rm -f .spotify_token_cache
```

## 6. Daily Launch

Shortest form (if venv already created):

```bash
cd <project-root> && source .venv-tk/bin/activate && python main.py
```

Or use launcher script:

```bash
./run.sh
```

Enable global hotkeys:

```bash
./run.sh --hotkeys
```

## UI Controls

- `Prev` / `Next`: track navigation
- `Play/Pause`: toggle playback
- `-10s` / `+10s`: seek
- `Queue Top`: enter a new shuffled queue frame from top tracks
- `Hop In Album`: push current frame and switch to album context
- `Hop Out`: pop one frame and restore prior context/queue

## Global Hotkeys

- `F13`: Prev
- `F14`: Hop In Album
- `F15`: Next
- `F16`: -10s
- `F17`: Queue Top
- `F18`: +10s
- `F19`: Hop Out
- `F20`: Play/Pause

Notes:
- Hotkeys are opt-in via `--hotkeys` (or `SP_STACK_HOTKEYS=1`).
- On some macOS setups, global keyboard hooks can fail; UI still works.

## Troubleshooting

### `ModuleNotFoundError: No module named '_tkinter'`
Your Python lacks Tk. Install python.org Python and recreate `.venv-tk`.

### `INVALID_CLIENT: Invalid redirect URI`
Mismatch between `.env` and Spotify app settings. Both must be exactly:
`http://127.0.0.1:8888/callback`

### Browser opens repeatedly / asks auth every click
Usually bad redirect URI or stale token cache.

```bash
rm -f .spotify_token_cache
```

Then relaunch after confirming `.env` and Spotify dashboard URI match.

### No active playback
Spotify APIs need an active device/session. Start playback in Spotify app first, then retry.

## Project Layout

- `main.py`: launch entrypoint
- `run.sh`: convenience launcher
- `spotify_stack/controller.py`: stack playback logic
- `spotify_stack/ui.py`: Tk UI
- `spotify_stack/hotkeys.py`: global hotkeys integration
- `spotify_stack/app.py`: app/bootstrap + auth wiring
- `tests/test_controller.py`: stack behavior unit tests

## Tests

```bash
cd <project-root>
source .venv-tk/bin/activate
python -m unittest discover -s tests -p 'test_*.py'
```
