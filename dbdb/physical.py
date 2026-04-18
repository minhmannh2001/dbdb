"""Append-only file storage (physical layer). Built incrementally per roadmap."""

import os
import struct


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

    def _bytes_to_integer(self, integer_bytes: bytes) -> int:
        return struct.unpack(self.INTEGER_FORMAT, integer_bytes)[0]

    def _integer_to_bytes(self, integer: int) -> bytes:
        return struct.pack(self.INTEGER_FORMAT, integer)

    def _read_integer(self) -> int:
        return self._bytes_to_integer(self._f.read(self.INTEGER_LENGTH))

    def _write_integer(self, integer: int) -> None:
        self._f.write(self._integer_to_bytes(integer))

    def write(self, data: bytes) -> int:
        self._seek_end()
        object_address = self._f.tell()
        self._f.write(self._integer_to_bytes(len(data)))
        self._f.write(data)
        return object_address

    def read(self, address: int) -> bytes:
        self._f.seek(address)
        length = self._read_integer()
        return self._f.read(length)

    def get_root_address(self) -> int:
        self._seek_superblock()
        return self._read_integer()

    def commit_root_address(self, root_address: int) -> None:
        self._f.flush()
        self._seek_superblock()
        self._write_integer(root_address)
        self._f.flush()
