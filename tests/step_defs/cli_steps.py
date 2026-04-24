# tests/step_defs/cli_steps.py
import os
import subprocess
import sys
import pytest
from pytest_bdd import given, when, then, parsers

import dbdb


@pytest.fixture
def context():
    return {}


@given(parsers.parse('a database file "{dbname}" with key "{key}" set to "{value}"'))
def populated_db_file(dbname, key, value):
    if os.path.exists(dbname):
        os.remove(dbname)
    db = dbdb.connect(dbname)
    db[key] = value
    db.commit()
    db.close()
    yield
    os.remove(dbname)


@given(parsers.parse('an empty database file "{dbname}"'))
def empty_db_file(dbname):
    if os.path.exists(dbname):
        os.remove(dbname)
    yield
    if os.path.exists(dbname):
        os.remove(dbname)


@when(parsers.parse('I run the command "{command}" on "{dbname}"'))
def run_cli_command(command, dbname, context):
    # We need to construct the full command to run via subprocess
    full_command = [
        sys.executable,  # Use the same python interpreter running pytest
        "-m",
        "dbdb.tool",
        dbname,
    ] + command.split()

    result = subprocess.run(
        full_command,
        capture_output=True,
        text=True,  # To get stdout/stderr as strings
    )
    context["result"] = result


@then("the command should succeed")
def command_should_succeed(context):
    assert context["result"].returncode == 0
    assert context["result"].stderr == ""


@then(parsers.parse('the standard output should be exactly "{output}"'))
def stdout_should_be(context, output):
    # The reference tool doesn't add a newline, so we don't either.
    assert context["result"].stdout == output
