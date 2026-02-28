import os

from spotify_stack import run_app


if __name__ == "__main__":
    # Some macOS environments can abort when initializing global keyboard hooks.
    # Keep the app usable by default; opt-in to hotkeys with SP_STACK_HOTKEYS=1.
    run_app(enable_hotkeys=os.getenv("SP_STACK_HOTKEYS") == "1")
