"""Unit tests for ValueRef (logical layer)."""

import io

from dbdb.logical import ValueRef
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
