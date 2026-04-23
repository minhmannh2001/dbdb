# tests/step_defs/connect_function_steps.py
import os
import tempfile
import pytest
from pytest_bdd import given, when, then, parsers

import dbdb
from dbdb.interface import DBDB


@pytest.fixture
def context():
    return {}


@given("a non-existent temporary database path", target_fixture="context")
def non_existent_temp_db_path():
    # Create a temp file and immediately delete it to get a valid, non-existent path
    with tempfile.NamedTemporaryFile(delete=True) as f:
        path = f.name
    return {"path": path}


@when("I connect to the database at that path")
def connect_to_path_simple(context):
    conn = dbdb.connect(context["path"])
    context["conn"] = conn


@when("I connect to the database at that file's path")
def connect_to_path_from_file(context):
    conn = dbdb.connect(context["path"])
    context["conn"] = conn


@then("a file should exist at that path")
def file_should_exist(context):
    assert os.path.exists(context["path"])
    # Clean up the created file
    if "conn" in context:
        context["conn"].close()
    os.remove(context["path"])


@then("the connection should be a DBDB instance")
def connection_is_dbdb_instance(context):
    assert isinstance(context["conn"], DBDB)


@given('a temporary database file with key "a" set to "1"', target_fixture="context")
def temp_db_with_data():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        path = f.name
    db = dbdb.connect(path)
    db["a"] = "1"
    db.commit()
    db.close()
    return {"path": path}


@then(
    parsers.parse('getting the key "{key}" from the connection should return "{value}"')
)
def get_key_from_connection(context, key, value):
    assert context["conn"][key] == value
    # Clean up
    context["conn"].close()
    os.remove(context["path"])
