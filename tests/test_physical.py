import io
import os
import struct
import tempfile

from dbdb.physical import Storage


def test_storage_keeps_same_file_handle():
    buf = io.BytesIO()
    storage = Storage(buf)
    assert storage._f is buf


def test_storage_binary_layout_constants():
    """Match reference 500L layout: superblock size + big-endian uint64 length prefix."""
    assert Storage.SUPERBLOCK_SIZE == 4096
    assert Storage.INTEGER_FORMAT == "!Q"
    assert Storage.INTEGER_LENGTH == 8
    assert struct.calcsize(Storage.INTEGER_FORMAT) == Storage.INTEGER_LENGTH


def test_seek_superblock_moves_cursor_to_start():
    buf = io.BytesIO(b"xyzzy")
    storage = Storage(buf)
    buf.seek(3)
    storage._seek_superblock()
    assert buf.tell() == 0


def test_seek_end_moves_cursor_to_eof():
    buf = io.BytesIO(b"hello")
    storage = Storage(buf)
    buf.seek(0)
    storage._seek_end()
    assert buf.tell() == len(buf.getvalue())


def test_init_ensures_superblock_on_empty_file():
    """New backing store is padded to SUPERBLOCK_SIZE with zeros (reference behavior)."""
    empty_superblock = b"\x00" * Storage.SUPERBLOCK_SIZE
    f = tempfile.NamedTemporaryFile(mode="r+b", delete=False)
    try:
        Storage(f)
        f.flush()
        f.seek(0, os.SEEK_END)
        assert f.tell() == Storage.SUPERBLOCK_SIZE
        f.seek(0)
        assert f.read() == empty_superblock
    finally:
        f.close()
        os.unlink(f.name)
