# tests/test_tool.py
import os
import subprocess
import sys
import tempfile
import pytest

import dbdb


@pytest.fixture
def temp_db_path():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        yield f.name
    os.remove(f.name)


def run_tool(db_path, args):
    base_command = [sys.executable, "-m", "dbdb.tool", db_path]
    return subprocess.run(
        base_command + args,
        capture_output=True,
        text=True,
    )


class TestTool:
    def test_get_command(self, temp_db_path):
        # Setup DB
        db = dbdb.connect(temp_db_path)
        db["a"] = "123"
        db.commit()
        db.close()

        # Run `get` and check output
        result = run_tool(temp_db_path, ["get", "a"])
        assert result.returncode == 0
        assert result.stdout == "123"
        assert result.stderr == ""

    def test_set_commit_get_commands(self, temp_db_path):
        # Run `set`
        result_set = run_tool(temp_db_path, ["set", "b", "456"])
        assert result_set.returncode == 0
        assert result_set.stdout == ""
        assert result_set.stderr == ""

        # Run `commit`
        result_commit = run_tool(temp_db_path, ["commit"])
        assert result_commit.returncode == 0
        assert result_commit.stdout == ""
        assert result_commit.stderr == ""

        # Run `get` to verify
        result_get = run_tool(temp_db_path, ["get", "b"])
        assert result_get.returncode == 0
        assert result_get.stdout == "456"
        assert result_get.stderr == ""

    def test_delete_command(self, temp_db_path):
        # Setup
        run_tool(temp_db_path, ["set", "c", "789"])
        # No need to commit, `set` autocommits

        # Run `delete`
        result_delete = run_tool(temp_db_path, ["delete", "c"])
        assert result_delete.returncode == 0

        # Verify with `get`
        result_get = run_tool(temp_db_path, ["get", "c"])
        assert result_get.returncode != 0

    def test_delete_missing_key_fails(self, temp_db_path):
        # Run `delete` on a non-existent key
        result_delete = run_tool(temp_db_path, ["delete", "non-existent"])
        assert result_delete.returncode != 0
        assert "Key not found" in result_delete.stderr
