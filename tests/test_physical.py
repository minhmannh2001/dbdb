import io
import os
import struct
import tempfile
from unittest.mock import patch

import pytest

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


def test_write_appends_big_endian_length_then_payload():
    """After superblock, each record is uint64_be length + bytes (reference layout)."""
    buf = io.BytesIO()
    storage = Storage(buf)
    addr = storage.write(b"ABCDE")
    assert addr == Storage.SUPERBLOCK_SIZE
    raw = buf.getvalue()
    _, data_region = raw[: Storage.SUPERBLOCK_SIZE], raw[Storage.SUPERBLOCK_SIZE :]
    assert data_region == struct.pack(Storage.INTEGER_FORMAT, 5) + b"ABCDE"


def test_write_sequential_records_chain_offsets():
    buf = io.BytesIO()
    storage = Storage(buf)
    a1 = storage.write(b"A")
    a2 = storage.write(b"BB")
    assert a1 == Storage.SUPERBLOCK_SIZE
    assert a2 == Storage.SUPERBLOCK_SIZE + Storage.INTEGER_LENGTH + 1
    tail = buf.getvalue()[Storage.SUPERBLOCK_SIZE :]
    assert tail == (
        struct.pack(Storage.INTEGER_FORMAT, 1)
        + b"A"
        + struct.pack(Storage.INTEGER_FORMAT, 2)
        + b"BB"
    )


def test_read_after_manual_record_at_superblock_boundary():
    """Same layout as reference test_read: length prefix then payload."""
    buf = io.BytesIO(b"\x00" * Storage.SUPERBLOCK_SIZE)
    buf.seek(Storage.SUPERBLOCK_SIZE)
    buf.write(b"\x00\x00\x00\x00\x00\x00\x00\x0801234567")
    buf.seek(0)
    storage = Storage(buf)
    assert storage.read(Storage.SUPERBLOCK_SIZE) == b"01234567"


def test_write_then_read_roundtrip_various_payloads():
    buf = io.BytesIO()
    storage = Storage(buf)
    for payload in (b"", b"x", b"\xff\x00", b"hello world"):
        addr = storage.write(payload)
        assert storage.read(addr) == payload


def test_read_write_integer_at_start_of_superblock():
    """First eight bytes of file hold root address (big-endian uint64); helpers use current offset."""
    buf = io.BytesIO()
    storage = Storage(buf)
    storage._seek_superblock()
    storage._write_integer(257)
    assert buf.getvalue()[:8] == b"\x00\x00\x00\x00\x00\x00\x01\x01"
    storage._seek_superblock()
    assert storage._read_integer() == 257


def test_read_integer_from_superblock_start_after_manual_write():
    buf = io.BytesIO(b"\x00" * Storage.SUPERBLOCK_SIZE)
    buf.seek(0)
    buf.write(b"\x00\x00\x00\x00\x00\x00\x02\x02")
    buf.seek(0)
    storage = Storage(buf)
    storage._seek_superblock()
    assert storage._read_integer() == 514


def test_get_root_address_is_zero_on_fresh_store():
    buf = io.BytesIO()
    storage = Storage(buf)
    assert storage.get_root_address() == 0


def test_get_root_address_reads_uint64_at_file_start():
    buf = io.BytesIO(b"\x00" * Storage.SUPERBLOCK_SIZE)
    buf.seek(0)
    buf.write(b"\x00\x00\x00\x00\x00\x00\x02\x02")
    buf.seek(0)
    storage = Storage(buf)
    assert storage.get_root_address() == 514


def test_commit_root_address_writes_uint64_at_file_start():
    buf = io.BytesIO()
    storage = Storage(buf)
    storage.commit_root_address(257)
    assert buf.getvalue()[:8] == b"\x00\x00\x00\x00\x00\x00\x01\x01"


def test_get_root_address_matches_value_after_commit():
    buf = io.BytesIO()
    storage = Storage(buf)
    storage.commit_root_address(12_345)
    assert storage.get_root_address() == 12_345


def test_unlock_when_not_locked_does_not_raise():
    buf = io.BytesIO()
    storage = Storage(buf)
    storage.unlock()
    assert storage.locked is False


def test_double_lock_on_real_file_second_returns_false():
    """Re-entrant style: second lock() must not call portalocker again (no deadlock)."""
    f = tempfile.NamedTemporaryFile(mode="r+b", delete=False)
    path = f.name
    try:
        storage = Storage(f)
        assert storage.lock() is True
        assert storage.locked is True
        assert storage.lock() is False
        assert storage.locked is True
        storage.unlock()
        assert storage.locked is False
        assert storage.lock() is True
        storage.unlock()
    finally:
        f.close()
        os.unlink(path)


def test_commit_root_address_calls_fsync_when_fd_available():
    f = tempfile.NamedTemporaryFile(mode="r+b", delete=False)
    path = f.name
    try:
        with patch("dbdb.physical.os.fsync") as mock_fsync:
            storage = Storage(f)
            storage.commit_root_address(42)
        assert mock_fsync.call_count == 2
    finally:
        f.close()
        os.unlink(path)


def test_storage_closed_matches_underlying_file_object():
    buf = io.BytesIO()
    storage = Storage(buf)
    assert storage.closed is False
    assert buf.closed is False
    storage.close()
    assert storage.closed is True
    assert buf.closed is True


def test_read_after_close_raises():
    buf = io.BytesIO()
    storage = Storage(buf)
    addr = storage.write(b"payload")
    storage.close()
    with pytest.raises(ValueError):
        storage.read(addr)


def test_close_unlocks_after_write_on_real_file():
    f = tempfile.NamedTemporaryFile(mode="r+b", delete=False)
    path = f.name
    try:
        storage = Storage(f)
        storage.write(b"x")
        assert storage.locked is True
        storage.close()
        assert storage.locked is False
        assert storage.closed is True
    finally:
        if not f.closed:
            f.close()
        os.unlink(path)


def test_workflow_writes_commits_root_reads_roundtrip():
    """Port of reference test_workflow: append records, move root, reads stay valid."""
    f = tempfile.NamedTemporaryFile(mode="r+b", delete=False)
    path = f.name
    try:
        storage = Storage(f)
        a1 = storage.write(b"one")
        a2 = storage.write(b"two")
        storage.commit_root_address(a2)
        a3 = storage.write(b"three")
        assert storage.get_root_address() == a2
        a4 = storage.write(b"four")
        storage.commit_root_address(a4)
        assert storage.read(a1) == b"one"
        assert storage.read(a2) == b"two"
        assert storage.read(a3) == b"three"
        assert storage.read(a4) == b"four"
        assert storage.get_root_address() == a4
    finally:
        f.close()
        os.unlink(path)
