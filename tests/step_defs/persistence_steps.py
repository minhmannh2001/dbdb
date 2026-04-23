# tests/step_defs/persistence_steps.py
import tempfile
import pytest
from pytest_bdd import given, when, then, parsers

from dbdb.physical import Storage
from dbdb.binary_tree import BinaryTree


@pytest.fixture
def context():
    return {}


@given("a new, empty database file", target_fixture="db_file")
def new_empty_database_file():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        return f.name


@when("I connect to the database")
def connect_to_database(db_file, context):
    f = open(db_file, "r+b")
    storage = Storage(f)
    tree = BinaryTree(storage)
    context["tree"] = tree
    context["storage"] = storage
    context["file_handle"] = f


@when(parsers.parse('I set the key "{key}" to the value "{value}"'))
def set_key_to_value(context, key, value):
    context["tree"].set(key, value)


@when("I commit the changes")
def commit_changes(context):
    context["tree"].commit()


@when("I close the database")
def close_database(context):
    context["storage"].close()
    # The underlying file handle is also closed by storage.close()


@when("I reconnect to the database")
def reconnect_to_database(db_file, context):
    # This is the same as the initial connect step
    connect_to_database(db_file, context)


@then(parsers.parse('getting the key "{key}" should return the value "{value}"'))
def get_key_returns_value(context, key, value):
    retrieved_value = context["tree"].get(key)
    assert retrieved_value == value


@then(parsers.parse('getting the key "{key}" should result in an error'))
def get_key_raises_error(context, key):
    with pytest.raises(KeyError):
        context["tree"].get(key)
