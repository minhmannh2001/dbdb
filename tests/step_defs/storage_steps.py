"""Step definitions for storage.feature."""

import io

from pytest_bdd import given, then, when

from dbdb.physical import Storage


@given("a binary in-memory file", target_fixture="memfile")
def binary_in_memory_file():
    return io.BytesIO()


@when("we construct Storage with that file", target_fixture="storage")
def construct_storage(memfile):
    return Storage(memfile)


@then("the storage exposes the same file handle")
def storage_same_handle(memfile, storage):
    assert storage._f is memfile
