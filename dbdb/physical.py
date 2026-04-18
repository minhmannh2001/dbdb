"""Append-only file storage (physical layer). Built incrementally per roadmap."""


class Storage:
    """Wraps a binary file-like object (must support read/write/seek/tell/flush)."""

    def __init__(self, f):
        self._f = f
