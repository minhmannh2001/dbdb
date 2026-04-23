# tests/step_defs/interface_steps.py
import io
import pytest
from pytest_bdd import given, when, then, parsers

# This import will fail until the class is created
from dbdb.interface import DBDB
from dbdb.physical import Storage
from dbdb.binary_tree import BinaryTree


@pytest.fixture
def context():
    return {}


@given("a temporary file object", target_fixture="temp_file")
def temp_file_object():
    return io.BytesIO()


@when("I create a DBDB instance with the file object")
def create_dbdb_instance(temp_file, context):
    db = DBDB(temp_file)
    context["db"] = db


@then("the DBDB instance should be successfully created")
def dbdb_instance_created(context):
    assert "db" in context
    assert isinstance(context["db"], DBDB)


@then("the instance should have a private Storage object")
def instance_has_storage(context):
    assert hasattr(context["db"], "_storage")
    assert isinstance(context["db"]._storage, Storage)


@then("the instance should have a private BinaryTree object")
def instance_has_tree(context):
    assert hasattr(context["db"], "_tree")
    assert isinstance(context["db"]._tree, BinaryTree)


@given("a DBDB instance with a temporary file", target_fixture="context")
def dbdb_instance_with_temp_file():
    f = io.BytesIO()
    db = DBDB(f)
    return {"db": db, "file": f}


@when(parsers.parse('I set the key "{key}" to "{value}" in the database'))
def set_key_in_db(context, key, value):
    context["db"][key] = value


@then(
    parsers.parse('getting the key "{key}" from the database should return "{value}"')
)
def get_key_from_db_returns_value(context, key, value):
    assert context["db"][key] == value


@when(parsers.parse('I delete the key "{key}" from the database'))
def delete_key_from_db(context, key):
    del context["db"][key]


@then(
    parsers.parse('getting the key "{key}" from the database should raise a KeyError')
)
def get_key_from_db_raises_key_error(context, key):
    with pytest.raises(KeyError):
        _ = context["db"][key]


@when("I close the database instance")
def close_db_instance(context):
    context["db"].close()


@when("I commit the database changes")
def commit_db_changes(context):
    context["db"].commit()


@when("I reopen the database from the same file")
def reopen_db(context):
    f = context["file"]
    f.seek(0)
    context["db"] = DBDB(f)


@then(parsers.parse('setting the key "{key}" to "{value}" should raise a ValueError'))
def set_key_on_closed_db_raises_value_error(context, key, value):
    with pytest.raises(ValueError):
        context["db"][key] = value


@then(parsers.parse('getting the key "{key}" should raise a ValueError'))
def get_key_on_closed_db_raises_value_error(context, key):
    with pytest.raises(ValueError):
        _ = context["db"][key]


@then(parsers.parse('deleting the key "{key}" should raise a ValueError'))
def delete_key_on_closed_db_raises_value_error(context, key):
    with pytest.raises(ValueError):
        del context["db"][key]


@then(parsers.parse('the key "{key}" should exist in the database'))
def key_should_exist(context, key):
    assert key in context["db"]


@then(parsers.parse('the key "{key}" should not exist in the database'))
def key_should_not_exist(context, key):
    assert key not in context["db"]


@then(parsers.parse("the length of the database should be {length:d}"))
def db_length_should_be(context, length):
    assert len(context["db"]) == length
