# tests/step_defs/compaction_steps.py
import os
import tempfile
import pytest
from pytest_bdd import given, when, then

import dbdb


@pytest.fixture
def context():
    return {}


@given("a database with overwritten data", target_fixture="context")
def db_with_overwritten_data():
    f = tempfile.NamedTemporaryFile(delete=False)
    path = f.name
    f.close()

    db = dbdb.connect(path)
    db["a"] = "1"  # This will be garbage
    db["b"] = "2"
    db.commit()
    db["a"] = "3"  # This is the final value
    db.commit()
    db.close()
    return {"path": path}


@when("I get the initial file size")
def get_initial_size(context):
    context["initial_size"] = os.path.getsize(context["path"])


@when("I compact the database")
def compact_db(context):
    db = dbdb.connect(context["path"])
    db.compact()
    db.close()


@then("the new file size should be smaller")
def new_size_smaller(context):
    new_size = os.path.getsize(context["path"])
    assert new_size < context["initial_size"]


@then("the database should contain the latest data")
def db_contains_latest_data(context):
    db = dbdb.connect(context["path"])
    assert db["a"] == "3"
    assert db["b"] == "2"
    assert len(db) == 2
    db.close()
    os.remove(context["path"])
