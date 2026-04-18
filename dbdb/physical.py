"""Append-only file storage (physical layer). Built incrementally per roadmap."""

import os


class Storage:
    """Wraps a binary file-like object (must support read/write/seek/tell/flush)."""

    SUPERBLOCK_SIZE = 4096
    INTEGER_FORMAT = "!Q"
    INTEGER_LENGTH = 8

    def __init__(self, f):
        self._f = f
        self._ensure_superblock()

    def _ensure_superblock(self):
        self._seek_end()
        end_address = self._f.tell()
        if end_address < self.SUPERBLOCK_SIZE:
            self._f.write(b"\x00" * (self.SUPERBLOCK_SIZE - end_address))

    def _seek_end(self):
        self._f.seek(0, os.SEEK_END)

    def _seek_superblock(self):
        self._f.seek(0)
