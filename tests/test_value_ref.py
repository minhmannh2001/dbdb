"""Unit tests for ValueRef (logical layer)."""

import io

import pytest

from dbdb.logical import BytesValueRef, ValueRef
from dbdb.physical import Storage


def test_value_ref_constructible_with_defaults():
    ref = ValueRef()
    assert ref.address == 0


def test_value_ref_accepts_explicit_address():
    ref = ValueRef(address=4096)
    assert ref.address == 4096


def test_value_ref_accepts_referent_and_address():
    ref = ValueRef("hello", 99)
    assert ref.address == 99


def test_prepare_to_store_default_does_nothing():
    ref = ValueRef()
    ref.prepare_to_store(object())


class _RecordingValueRef(ValueRef):
    def __init__(self):
        super().__init__()
        self.seen_storage = None

    def prepare_to_store(self, storage):
        self.seen_storage = storage


def test_subclass_can_override_prepare_to_store():
    storage = object()
    ref = _RecordingValueRef()
    ref.prepare_to_store(storage)
    assert ref.seen_storage is storage


def test_referent_to_bytes_utf8():
    assert ValueRef.referent_to_bytes("hello") == b"hello"


def test_bytes_to_referent_utf8_roundtrip():
    original = "café"
    blob = ValueRef.referent_to_bytes(original)
    assert ValueRef.bytes_to_referent(blob) == original


def test_referent_to_bytes_preserves_multibyte_utf8():
    s = "\u3042"
    b = ValueRef.referent_to_bytes(s)
    assert b == "\u3042".encode("utf-8")
    assert ValueRef.bytes_to_referent(b) == s


def test_get_loads_referent_from_storage_when_only_address():
    buf = io.BytesIO()
    storage = Storage(buf)
    addr = storage.write(ValueRef.referent_to_bytes("persisted"))
    ref = ValueRef(referent=None, address=addr)
    assert ref.get(storage) == "persisted"


def test_get_returns_none_when_no_address():
    buf = io.BytesIO()
    ref = ValueRef()
    assert ref.get(Storage(buf)) is None


def test_get_returns_referent_without_read_when_already_in_memory():
    buf = io.BytesIO()
    storage = Storage(buf)
    addr = storage.write(ValueRef.referent_to_bytes("disk"))
    ref = ValueRef("ram wins", addr)
    assert ref.get(storage) == "ram wins"


def test_store_writes_payload_and_sets_address():
    buf = io.BytesIO()
    storage = Storage(buf)
    ref = ValueRef("persist me")
    ref.store(storage)
    assert ref.address == Storage.SUPERBLOCK_SIZE


def test_store_then_get_roundtrip_on_fresh_ref():
    buf = io.BytesIO()
    storage = Storage(buf)
    ref = ValueRef("roundtrip")
    ref.store(storage)
    loaded = ValueRef(referent=None, address=ref.address)
    assert loaded.get(storage) == "roundtrip"


def test_store_skips_when_no_referent():
    buf = io.BytesIO()
    storage = Storage(buf)
    ref = ValueRef()
    ref.store(storage)
    assert ref.address == 0


def test_store_skips_when_address_already_set():
    buf = io.BytesIO()
    storage = Storage(buf)
    ref = ValueRef("ignored", address=123)
    ref.store(storage)
    assert ref.address == 123


def test_store_calls_prepare_to_store_before_write():
    buf = io.BytesIO()
    storage = Storage(buf)

    class _PreparingRef(ValueRef):
        def __init__(self):
            super().__init__("payload", 0)
            self.prepared = False

        def prepare_to_store(self, storage):
            self.prepared = True

    ref = _PreparingRef()
    ref.store(storage)
    assert ref.prepared is True
    assert ref.address == Storage.SUPERBLOCK_SIZE


def test_bytes_value_ref_init_accepts_bytes():
    ref = BytesValueRef(b"\x00\xff")
    assert ref.get(Storage(io.BytesIO())) == b"\x00\xff"


def test_bytes_value_ref_init_rejects_str():
    with pytest.raises(TypeError):
        BytesValueRef("not bytes")


def test_bytes_value_ref_normalizes_bytearray_to_bytes():
    ref = BytesValueRef(bytearray([1, 2, 3]))
    assert ref.get(Storage(io.BytesIO())) == b"\x01\x02\x03"


def test_bytes_value_ref_store_then_get_roundtrip():
    buf = io.BytesIO()
    storage = Storage(buf)
    ref = BytesValueRef(b"\xde\xad\xbe\xef")
    ref.store(storage)
    loaded = BytesValueRef(referent=None, address=ref.address)
    assert loaded.get(storage) == b"\xde\xad\xbe\xef"


def test_bytes_value_ref_static_roundtrip():
    payload = b"\xff\x00"
    assert BytesValueRef.bytes_to_referent(BytesValueRef.referent_to_bytes(payload)) == payload
