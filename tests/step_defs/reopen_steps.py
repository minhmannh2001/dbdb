# tests/step_defs/reopen_steps.py
import os
import tempfile
from unittest.mock import patch

import pytest
from pytest_bdd import given, when, then, parsers

import dbdb


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _simulate_replacement(original_path: str, data: dict) -> None:
    """Write a new db file with given data and atomically rename over original."""
    tmp_path = original_path + ".replacement"
    new_db = dbdb.connect(tmp_path)
    try:
        for key, value in data.items():
            new_db[key] = value
        new_db.commit()
    finally:
        new_db.close()
    os.rename(tmp_path, original_path)


# ---------------------------------------------------------------------------
# Background
# ---------------------------------------------------------------------------

@given("a database at a temporary path", target_fixture="context")
def database_at_temp_path():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    db = dbdb.connect(path)
    ctx = {"path": path, "db": db}
    yield ctx
    if not db._storage.closed:
        db.close()
    if os.path.exists(path):
        os.remove(path)


# ---------------------------------------------------------------------------
# Given
# ---------------------------------------------------------------------------

@given(parsers.parse('the database has key "{key}" set to "{value}"'))
def db_has_key(context, key, value):
    context["db"][key] = value


@given("I commit the original connection")
def commit_original(context):
    context["db"].commit()


@given(parsers.parse('another process replaces the file with key "{key}" set to "{value}"'))
def another_process_replaces_with_one_key(context, key, value):
    context["db"].commit()
    context["db"]._storage.unlock()
    _simulate_replacement(context["path"], {key: value})


@given("another process replaces the file keeping both keys")
def another_process_replaces_keeping_both(context):
    path = context["path"]
    existing = {k: context["db"][k] for k in context["db"]}
    _simulate_replacement(path, existing)


# ---------------------------------------------------------------------------
# When
# ---------------------------------------------------------------------------

@when(parsers.parse('I read key "{key}" from the original connection'))
def read_key_from_original(context, key):
    context["result"] = context["db"][key]


@when(parsers.parse('I set key "{key}" to "{value}" on the original connection and commit'))
def set_key_and_commit(context, key, value):
    context["db"][key] = value
    context["db"].commit()


@when(parsers.parse('I set key "{key}" to "{value}" on the original connection'))
def set_key_no_commit(context, key, value):
    context["db"][key] = value


@when("I commit the original connection")
def when_commit_original(context):
    context["db"].commit()


@when(parsers.parse('I delete key "{key}" from the original connection and commit'))
def delete_key_and_commit(context, key):
    del context["db"][key]
    context["db"].commit()


@when(parsers.parse('I set key "{key}" to "{value}" bypassing the pre-lock check and commit'))
def set_key_bypassing_prelock(context, key, value):
    # Simulate the TOCTOU window: the pre-lock replacement check is bypassed
    # (returns without action), but the file was already replaced. The post-lock
    # check inside _prepare_write must catch it.
    with patch.object(context["db"], "_reopen_if_replaced", return_value=None):
        context["db"][key] = value
    context["db"].commit()


# ---------------------------------------------------------------------------
# Then
# ---------------------------------------------------------------------------

@then(parsers.parse('the result should be "{value}"'))
def result_should_be(context, value):
    assert context["result"] == value


@then(parsers.parse('a fresh connection should have key "{key}" equal to "{value}"'))
def fresh_connection_has_key(context, key, value):
    db = dbdb.connect(context["path"])
    try:
        assert db[key] == value
    finally:
        db.close()


@then(parsers.parse('a fresh connection should not have key "{key}"'))
def fresh_connection_missing_key(context, key):
    db = dbdb.connect(context["path"])
    try:
        assert key not in db
    finally:
        db.close()
