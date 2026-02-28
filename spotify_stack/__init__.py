"""Spotify Stack Player package."""

__all__ = ["run_app"]


def run_app(*args, **kwargs):
    # Import lazily so tests can run in headless runtimes without tkinter.
    from .app import run_app as _run_app

    return _run_app(*args, **kwargs)
