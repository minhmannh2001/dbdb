"""Shared BDD steps reused by multiple domain features."""

import io

from pytest_bdd import given

from dbdb.physical import Storage


@given("empty storage over a binary memory buffer", target_fixture="storage")
def empty_storage_over_binary_memory_buffer():
    return Storage(io.BytesIO())
