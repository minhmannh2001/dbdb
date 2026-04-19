"""Step definitions for storage.feature."""

import io

from pytest_bdd import given, then, when

from dbdb.physical import Storage

_STORAGE_ROUNDTRIP_PAYLOAD = b"dbdb-storage-bdd-roundtrip"


@given("a binary in-memory file", target_fixture="memfile")
def binary_in_memory_file():
    return io.BytesIO()


@when("we construct Storage with that file", target_fixture="storage")
def construct_storage(memfile):
    return Storage(memfile)


@then("the storage exposes the same file handle")
def storage_same_handle(memfile, storage):
    assert storage._f is memfile


@when("we append a known byte payload through write", target_fixture="write_address")
def append_known_payload(storage):
    return storage.write(_STORAGE_ROUNDTRIP_PAYLOAD)


@when("we read the blob at that write address", target_fixture="read_back")
def read_blob_at_address(storage, write_address):
    return storage.read(write_address)


@then("the read bytes equal the appended payload")
def read_matches_appended(read_back):
    assert read_back == _STORAGE_ROUNDTRIP_PAYLOAD
