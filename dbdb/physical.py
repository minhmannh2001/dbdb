"""Append-only file storage (physical layer). Built incrementally per roadmap."""

import io
import os
import struct

import portalocker


class Storage:
    """Wraps a binary file-like object (must support read/write/seek/tell/flush)."""

    SUPERBLOCK_SIZE = 4096
    INTEGER_FORMAT = "!Q"
    INTEGER_LENGTH = 8

    def __init__(self, f):
        self._f = f
        self.locked = False
        self._ensure_superblock()

    def lock(self) -> bool:
        if not self.locked:
            try:
                portalocker.lock(self._f, portalocker.LOCK_EX)
            except io.UnsupportedOperation:
                # In-memory file-likes (e.g. BytesIO) have no fileno; keep self.locked semantics only.
                pass
            self.locked = True
            return True
        return False

    def unlock(self) -> None:
        if self.locked:
            self._f.flush()
            try:
                portalocker.unlock(self._f)
            except io.UnsupportedOperation:
                pass
            self.locked = False

    def _ensure_superblock(self):
        self.lock()
        self._seek_end()
        end_address = self._f.tell()
        if end_address < self.SUPERBLOCK_SIZE:
            self._f.write(b"\x00" * (self.SUPERBLOCK_SIZE - end_address))
        self.unlock()

    def _seek_end(self):
        self._f.seek(0, os.SEEK_END)

    def _seek_superblock(self):
        self._f.seek(0)

    def _fsync_if_possible(self) -> None:
        """Push buffered data to the storage device when the backing file has an FD.

        Skips in-memory buffers (no ``fileno``). ``OSError`` from odd FDs is ignored so
        commit can still complete on exotic streams (tradeoff: weaker guarantees there).
        """
        try:
            fd = self._f.fileno()
        except (AttributeError, io.UnsupportedOperation, OSError):
            return
        try:
            os.fsync(fd)
        except OSError:
            pass

    def _bytes_to_integer(self, integer_bytes: bytes) -> int:
        return struct.unpack(self.INTEGER_FORMAT, integer_bytes)[0]

    def _integer_to_bytes(self, integer: int) -> bytes:
        return struct.pack(self.INTEGER_FORMAT, integer)

    def _read_integer(self) -> int:
        return self._bytes_to_integer(self._f.read(self.INTEGER_LENGTH))

    def _write_integer(self, integer: int) -> None:
        self.lock()
        self._f.write(self._integer_to_bytes(integer))

    def write(self, data: bytes) -> int:
        self.lock()
        self._seek_end()
        object_address = self._f.tell()
        self._write_integer(len(data))
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
        """Persist root after appended payload is pushed toward the device.

        Ordering: ``flush`` → ``fsync`` (payload) → write 8-byte root at offset 0 →
        ``flush`` → ``fsync`` (root). That lowers the chance the superblock points at
        bytes that only lived in the process buffer. Tradeoffs: ``fsync`` adds latency
        and I/O load; it is not a full backup or cross-filesystem atomicity guarantee.
        """
        self.lock()
        self._f.flush()
        self._fsync_if_possible()
        self._seek_superblock()
        self._write_integer(root_address)
        self._f.flush()
        self._fsync_if_possible()
        self.unlock()

    def close(self) -> None:
        self.unlock()
        self._f.close()

    @property
    def closed(self) -> bool:
        return self._f.closed
