"""Append-only file storage (physical layer). Built incrementally per roadmap."""

import io
import os
import struct
import threading
from typing import IO

import portalocker


class Storage:
    """Wraps a binary file-like object (must support read/write/seek/tell/flush)."""

    SUPERBLOCK_SIZE = 4096
    INTEGER_FORMAT = "!Q"
    INTEGER_LENGTH = 8

    # fcntl locks (used by portalocker on Unix) are per-process, not per-thread.
    # Threads within the same process do not block each other with fcntl alone.
    # This dict maps a canonical file path to a threading.Lock that serializes
    # same-process threads before they attempt the OS-level file lock.
    _thread_locks: dict[str, threading.Lock] = {}
    _thread_locks_guard = threading.Lock()

    @classmethod
    def _get_thread_lock(cls, key: str) -> threading.Lock:
        with cls._thread_locks_guard:
            if key not in cls._thread_locks:
                cls._thread_locks[key] = threading.Lock()
            return cls._thread_locks[key]

    def __init__(self, f: IO):
        self._f = f
        self.locked = False
        try:
            self._lock_key = os.path.realpath(f.name)
            self._thread_lock = self._get_thread_lock(self._lock_key)
        except AttributeError:
            # BytesIO and other in-memory file-likes have no name.
            # Use a fresh per-instance lock so that id() reuse across objects
            # never returns a stale (already-acquired) lock from the class dict.
            self._lock_key = None
            self._thread_lock = threading.Lock()
        self._ensure_superblock()

    def lock(self) -> bool:
        if not self.locked:
            self._thread_lock.acquire()
            try:
                portalocker.lock(self._f, portalocker.LOCK_EX)
            except io.UnsupportedOperation:
                # In-memory file-likes (e.g. BytesIO) have no fileno; keep self.locked semantics only.
                pass
            except Exception:
                self._thread_lock.release()
                raise
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
            self._thread_lock.release()

    def _ensure_superblock(self) -> None:
        self.lock()
        self._seek_end()
        end_address = self._f.tell()
        if end_address < self.SUPERBLOCK_SIZE:
            self._f.write(b"\x00" * (self.SUPERBLOCK_SIZE - end_address))
        self.unlock()

    def _seek_end(self) -> None:
        self._f.seek(0, os.SEEK_END)

    def _seek_superblock(self) -> None:
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

    def _pread_superblock(self, offset: int, n: int) -> bytes:
        """Read n bytes at superblock offset, bypassing Python's read-ahead cache.

        BufferedRandom fills a read buffer on the first read and returns cached
        bytes on subsequent seeks within that range. Writes from other file handles
        to the same file are invisible through the stale buffer. os.pread() goes
        directly to the OS page cache, which reflects all flushed writes.
        Falls back to seek+read for in-memory file-likes (no fileno).
        """
        try:
            return os.pread(self._f.fileno(), n, offset)
        except (AttributeError, io.UnsupportedOperation, OSError):
            self._f.seek(offset)
            return self._f.read(n)

    def get_root_address(self) -> int:
        return self._bytes_to_integer(
            self._pread_superblock(0, self.INTEGER_LENGTH)
        )

    def get_tree_type(self) -> int:
        data = self._pread_superblock(self.INTEGER_LENGTH, 1)
        if not data:
            return 0
        return struct.unpack("!B", data)[0]

    def set_tree_type(self, tree_type: int) -> None:
        self.lock()
        self._seek_superblock()
        self._f.seek(self.INTEGER_LENGTH, os.SEEK_CUR)  # Skip root address
        self._f.write(struct.pack("!B", tree_type))
        self._f.flush()
        self._fsync_if_possible()
        self.unlock()

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

    def is_file_replaced(self) -> bool:
        """True if the file at our path was replaced since we opened it (e.g. by compaction)."""
        try:
            return os.fstat(self._f.fileno()).st_ino != os.stat(self._f.name).st_ino
        except (OSError, io.UnsupportedOperation):
            return False

    @property
    def closed(self) -> bool:
        return self._f.closed
