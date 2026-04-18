import io
import struct

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
    assert buf.tell() == 5
