"""Append-only file storage (physical layer). Built incrementally per roadmap."""

import os


class Storage:
    """Wraps a binary file-like object (must support read/write/seek/tell/flush)."""

    SUPERBLOCK_SIZE = 4096
    INTEGER_FORMAT = "!Q"
    INTEGER_LENGTH = 8

    def __init__(self, f):
        self._f = f

    def _seek_end(self):
        self._f.seek(0, os.SEEK_END)

    def _seek_superblock(self):
        self._f.seek(0)
