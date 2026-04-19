"""Step definitions for value_ref.feature."""

import pytest
from pytest_bdd import given, then, when

from dbdb.logical import BytesValueRef, ValueRef

_UTF8_ROUNDTRIP_TEXT = "caf\u00e9-bdd"


@given("a ValueRef holding UTF-8 text", target_fixture="text_ref")
def value_ref_holding_utf8():
    return ValueRef(_UTF8_ROUNDTRIP_TEXT)


@when("we store that reference on disk")
def store_value_ref(text_ref, storage):
    text_ref.store(storage)


@when("we open a second ValueRef that only knows the stored address", target_fixture="shadow_ref")
def second_ref_address_only(text_ref):
    return ValueRef(referent=None, address=text_ref.address)


@then("lazy get returns the original text")
def lazy_get_matches(shadow_ref, storage):
    assert shadow_ref.get(storage) == _UTF8_ROUNDTRIP_TEXT


@then("constructing BytesValueRef with a string referent raises TypeError")
def bytes_value_ref_string_raises():
    with pytest.raises(TypeError):
        BytesValueRef("plain string")
