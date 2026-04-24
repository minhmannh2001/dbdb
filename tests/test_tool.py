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
