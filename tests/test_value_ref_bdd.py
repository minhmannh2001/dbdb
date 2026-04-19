"""BDD: ValueRef and BytesValueRef observable contracts."""

from pytest_bdd import scenario


@scenario("value_ref.feature", "UTF-8 text roundtrips through store and lazy get")
def test_value_ref_utf8_roundtrip_bdd():
    pass


@scenario("value_ref.feature", "BytesValueRef rejects non-bytes referents at construction")
def test_bytes_value_ref_rejects_string_bdd():
    pass
